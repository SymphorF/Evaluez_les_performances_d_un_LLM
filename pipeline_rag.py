# Script avec toutes les étapes + Pydantic et Logfire
import os
import logging
import io
from pathlib import Path
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator

import fitz  # PyMuPDF pour lire les PDF

# Embeddings (exemple avec sentence-transformers)
try:
    from sentence_transformers import SentenceTransformer
    _HAS_ST = True
except ImportError:
    _HAS_ST = False

# Configuration du logging standard
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("DataPipeline")

# ---------------------------
# Schemas Pydantic V2
# ---------------------------
class DocumentIn(BaseModel):
    doc_id: str = Field(..., min_length=1, description="Identifiant unique du document")
    text: str = Field(..., min_length=1, description="Contenu textuel du document")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Métadonnées supplémentaires")
    
    @field_validator('text')
    @classmethod
    def text_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Le texte du document ne peut pas être vide')
        return v.strip()

class Chunk(BaseModel):
    chunk_id: str = Field(..., min_length=1, description="Identifiant unique du chunk")
    doc_id: str = Field(..., min_length=1, description="Document parent")
    text: str = Field(..., min_length=1, description="Texte du chunk")
    start_index: int = Field(..., ge=0, description="Index de début dans le document original")
    end_index: int = Field(..., ge=0, description="Index de fin dans le document original")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Métadonnées supplémentaires")
    
    @field_validator('text')
    @classmethod
    def chunk_text_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Le texte du chunk ne peut pas être vide')
        return v.strip()

class EmbeddingVec(BaseModel):
    chunk_id: str = Field(..., min_length=1, description="Identifiant du chunk correspondant")
    vector: List[float] = Field(..., min_length=1, description="Vecteur d'embedding")

# ---------------------------
# Pipeline avec structure Logfire prête
# ---------------------------
class DataPipeline:
    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 100):
        # Validation des paramètres
        if chunk_size <= 0:
            raise ValueError("chunk_size doit être positif")
        if chunk_overlap < 0:
            raise ValueError("chunk_overlap ne peut pas être négatif")
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap doit être inférieur à chunk_size")
            
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self._model = None
        self.embedding_dim = None
        
        logger.info(f"Pipeline initialisé - chunk_size: {chunk_size}, chunk_overlap: {chunk_overlap}")

    def _logfire_span(self, name: str, **kwargs):
        """Simulation de span Logfire - peut être remplacé plus tard"""
        logger.info(f"🔍 [LOGFIRE SPAN] {name} - {kwargs}")

    def _logfire_instrument(self, func):
        """Décorateur simulation Logfire instrument"""
        def wrapper(*args, **kwargs):
            self._logfire_span(f"start_{func.__name__}")
            result = func(*args, **kwargs)
            self._logfire_span(f"end_{func.__name__}")
            return result
        return wrapper

    def _extract_text_from_pdf(self, file_path: Path) -> str:
        """Extrait le texte d'un PDF avec plusieurs méthodes"""
        self._logfire_span("extraction_texte_pdf", file_name=file_path.name)
        text = ""
        
        try:
            # Méthode 1: Extraction standard avec PyMuPDF
            with fitz.open(file_path) as doc:
                for page_num, page in enumerate(doc):
                    # Essayer différentes méthodes d'extraction
                    page_text = page.get_text()
                    
                    # Si le texte est vide, essayer avec un autre encodage
                    if not page_text or not page_text.strip():
                        page_text = page.get_text("text", sort=True)
                    
                    # Si toujours vide, essayer avec HTML
                    if not page_text or not page_text.strip():
                        page_text = page.get_text("html")
                    
                    if page_text and page_text.strip():
                        text += f"--- Page {page_num + 1} ---\n{page_text}\n"
                        logger.debug(f"  Page {page_num + 1}: {len(page_text)} caractères")
            
            logger.info(f"  ✅ Texte extrait: {len(text)} caractères")
            self._logfire_span("extraction_reussie", total_characters=len(text), pages=text.count("--- Page"))
            return text
            
        except Exception as e:
            logger.error(f"  ❌ Erreur extraction PDF {file_path.name}: {e}")
            self._logfire_span("extraction_erreur", error=str(e), file_name=file_path.name)
            return ""

    def _debug_directory(self, input_path: Path):
        """Affiche le contenu du répertoire pour debug"""
        self._logfire_span("debug_repertoire", path=str(input_path))
        logger.info(f"=== DEBUG RÉPERTOIRE: {input_path} ===")
        if not input_path.exists():
            logger.error(f"❌ Le répertoire n'existe pas: {input_path}")
            return
            
        logger.info(f"📁 Répertoire existe: {input_path}")
        
        all_files = list(input_path.iterdir())
        logger.info(f"📄 Total fichiers dans le répertoire: {len(all_files)}")
        
        for file in all_files:
            if file.is_file():
                file_info = f"  - {file.name} (taille: {file.stat().st_size} bytes, extension: {file.suffix})"
            else:
                file_info = f"  - {file.name} [DIR]"
            logger.info(file_info)
            
        # Fichiers supportés
        pdf_files = list(input_path.glob("*.pdf"))
        txt_files = list(input_path.glob("*.txt")) 
        md_files = list(input_path.glob("*.md"))
        
        logger.info(f"📊 Fichiers supportés: {len(pdf_files)} PDF, {len(txt_files)} TXT, {len(md_files)} MD")

    # --- Chargement des fichiers ---
    def load_files(self, input_dir: str) -> List[DocumentIn]:
        """Charge les documents depuis le répertoire d'entrée avec validation"""
        self._logfire_span("chargement_fichiers", input_dir=input_dir)
        input_path = Path(input_dir).absolute()
        
        # Debug du répertoire
        self._debug_directory(input_path)
        
        if not input_path.exists():
            raise FileNotFoundError(f"Le répertoire {input_dir} n'existe pas")
        
        documents = []
        
        # Chercher tous les fichiers supportés
        supported_files = list(input_path.glob("*.pdf")) + list(input_path.glob("*.txt")) + list(input_path.glob("*.md"))
        logger.info(f"🎯 Traitement de {len(supported_files)} fichiers supportés")
        
        for file in supported_files:
            self._logfire_span("traitement_fichier", file_name=file.name)
            try:
                logger.info(f"📖 Lecture de: {file.name}")
                
                if file.suffix.lower() == ".pdf":
                    logger.debug(f"  Format: PDF")
                    text = self._extract_text_from_pdf(file)
                    
                    if text.strip():
                        # Analyser la qualité du texte extrait
                        word_count = len(text.split())
                        char_count = len(text)
                        
                        document = DocumentIn(
                            doc_id=file.stem,
                            text=text,
                            metadata={
                                "file_type": "pdf", 
                                "file_name": file.name,
                                "file_size": file.stat().st_size,
                                "word_count": word_count,
                                "char_count": char_count,
                                "pages": text.count("--- Page")  # Estimation du nombre de pages
                            }
                        )
                        documents.append(document)
                        logger.info(f"  ✅ PDF chargé: {file.name} ({word_count} mots, {char_count} caractères)")
                        self._logfire_span("pdf_charge", file_name=file.name, words=word_count, characters=char_count)
                    else:
                        logger.warning(f"  ⚠️ PDF vide après extraction: {file.name}")
                        self._logfire_span("pdf_vide", file_name=file.name)
                
                elif file.suffix.lower() in [".txt", ".md"]:
                    logger.debug(f"  Format: {file.suffix}")
                    try:
                        with open(file, "r", encoding="utf-8") as f:
                            text = f.read()
                    except UnicodeDecodeError:
                        # Essayer avec un autre encodage si UTF-8 échoue
                        with open(file, "r", encoding="latin-1") as f:
                            text = f.read()
                    
                    if text.strip():
                        document = DocumentIn(
                            doc_id=file.stem,
                            text=text,
                            metadata={
                                "file_type": file.suffix[1:],
                                "file_name": file.name,
                                "file_size": file.stat().st_size
                            }
                        )
                        documents.append(document)
                        logger.info(f"  ✅ Fichier texte chargé: {file.name} ({len(text)} caractères)")
                        self._logfire_span("texte_charge", file_name=file.name, characters=len(text))
                    else:
                        logger.warning(f"  ⚠️ Fichier texte vide: {file.name}")
                        self._logfire_span("texte_vide", file_name=file.name)
                        
            except Exception as e:
                logger.error(f"  ❌ Erreur lecture {file.name}: {e}")
                self._logfire_span("erreur_fichier", error=str(e), file_name=file.name)
                continue

        logger.info(f"📦 {len(documents)} fichiers chargés avec succès")
        self._logfire_span("chargement_termine", documents_charges=len(documents))
        return documents

    # --- Nettoyage ---
    @staticmethod
    def clean_text(text: str) -> str:
        """Nettoie le texte en supprimant les caractères indésirables"""
        # Remplacement des caractères problématiques
        s = text.replace("\r", " ").replace("\t", " ").replace("\xa0", " ")
        # Suppression des espaces multiples
        s = " ".join(s.split())
        return s.strip()

    def clean_documents(self, docs: List[DocumentIn]) -> List[DocumentIn]:
        """Nettoie tous les documents"""
        self._logfire_span("nettoyage_documents", initial_count=len(docs))
        original_count = len(docs)
        cleaned = []
        
        for doc in docs:
            self._logfire_span("nettoyage_document", doc_id=doc.doc_id)
            try:
                cleaned_text = self.clean_text(doc.text)
                # Ne garder que les documents avec un contenu significatif
                if len(cleaned_text) >= 20:
                    doc.text = cleaned_text
                    cleaned.append(doc)
                    logger.debug(f"Document {doc.doc_id} nettoyé et conservé")
                    self._logfire_span("document_conserve", doc_id=doc.doc_id, length=len(cleaned_text))
                else:
                    logger.debug(f"Document {doc.doc_id} ignoré (trop court après nettoyage)")
                    self._logfire_span("document_ignore", doc_id=doc.doc_id, length=len(cleaned_text))
            except Exception as e:
                logger.warning(f"Erreur nettoyage document {doc.doc_id}: {e}")
                self._logfire_span("erreur_nettoyage", error=str(e), doc_id=doc.doc_id)
        
        removed_count = original_count - len(cleaned)
        logger.info(f"🧹 Nettoyage: {len(cleaned)}/{original_count} documents conservés ({removed_count} supprimés)")
        self._logfire_span("nettoyage_termine", kept=len(cleaned), removed=removed_count)
        
        return cleaned

    # --- Chunking ---
    def chunk_documents(self, docs: List[DocumentIn]) -> List[Chunk]:
        """Découpe les documents en chunks avec chevauchement"""
        self._logfire_span("decoupage_chunks", documents_count=len(docs))
        chunks = []
        total_docs = len(docs)
        
        for doc_idx, doc in enumerate(docs):
            self._logfire_span("decoupage_document", doc_id=doc.doc_id)
            text = doc.text
            pos = 0
            chunk_count = 0
            
            while pos < len(text):
                end = min(pos + self.chunk_size, len(text))
                piece = text[pos:end].strip()
                
                # Ne créer un chunk que si le texte n'est pas vide
                if piece:
                    chunk = Chunk(
                        chunk_id=f"{doc.doc_id}_{chunk_count}",
                        doc_id=doc.doc_id,
                        text=piece,
                        start_index=pos,
                        end_index=end,
                        metadata=doc.metadata.copy()  # Copier les métadonnées
                    )
                    chunks.append(chunk)
                    chunk_count += 1
                
                # Avancer en tenant compte du chevauchement
                if end == len(text):
                    break
                pos = max(end - self.chunk_overlap, pos + 1)
            
            logger.debug(f"Document {doc.doc_id} découpé en {chunk_count} chunks")
            self._logfire_span("document_decoupe", doc_id=doc.doc_id, chunks=chunk_count)
        
        logger.info(f"✂️ Chunking terminé: {len(chunks)} chunks créés à partir de {total_docs} documents")
        self._logfire_span("decoupage_termine", total_chunks=len(chunks), total_documents=total_docs)
        return chunks

    # --- Embeddings ---
    def _ensure_model(self):
        """Charge le modèle d'embedding si nécessaire"""
        if self._model is None:
            if not _HAS_ST:
                raise ImportError(
                    "sentence-transformers n'est pas installé. "
                    "Executez: pip install sentence-transformers"
                )
            logger.info("🔧 Chargement du modèle d'embedding sentence-transformers/all-MiniLM-L6-v2")
            self._logfire_span("chargement_modele_embedding")
            self._model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

    def generate_embeddings(self, chunks: List[Chunk]) -> List[EmbeddingVec]:
        """Génère les embeddings pour tous les chunks"""
        self._logfire_span("generation_embeddings", chunks_count=len(chunks))
        self._ensure_model()
        
        if not chunks:
            logger.warning("Aucun chunk à traiter pour les embeddings")
            self._logfire_span("aucun_chunk_embeddings")
            return []
        
        texts = [chunk.text for chunk in chunks]
        chunk_ids = [chunk.chunk_id for chunk in chunks]
        
        logger.info(f"🔢 Génération des embeddings pour {len(chunks)} chunks...")
        
        try:
            # Génération des embeddings avec barre de progression
            self._logfire_span("encodage_vecteurs")
            vectors = self._model.encode(
                texts, 
                convert_to_numpy=True, 
                show_progress_bar=True,
                batch_size=32
            )
            
            embeddings = []
            for i, vec in enumerate(vectors):
                embedding = EmbeddingVec(
                    chunk_id=chunk_ids[i],
                    vector=vec.tolist()
                )
                embeddings.append(embedding)
            
            self.embedding_dim = len(vectors[0]) if len(vectors) > 0 else None
            
            logger.info(f"✅ Embeddings générés: {len(embeddings)} vecteurs (dimension: {self.embedding_dim})")
            self._logfire_span("embeddings_generes", count=len(embeddings), dimensions=self.embedding_dim)
            return embeddings
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de la génération des embeddings: {e}")
            self._logfire_span("erreur_embeddings", error=str(e))
            raise

    # --- Pipeline complet ---
    def run(self, input_dir: str):
        """Exécute le pipeline complet de préparation des données"""
        self._logfire_span("pipeline_complet", input_dir=input_dir)
        logger.info("🚀 === DÉMARRAGE DU PIPELINE DE PRÉPARATION ===")
        
        try:
            # Étape 1: Chargement
            self._logfire_span("etape_chargement")
            docs = self.load_files(input_dir)
            if not docs:
                logger.warning("❌ Aucun document chargé - vérifiez le répertoire d'entrée")
                self._logfire_span("aucun_document_charge")
                return [], [], []
            
            # Étape 2: Nettoyage
            self._logfire_span("etape_nettoyage")
            docs = self.clean_documents(docs)
            if not docs:
                logger.warning("❌ Aucun document conservé après nettoyage")
                self._logfire_span("aucun_document_conserve")
                return [], [], []
            
            # Étape 3: Chunking
            self._logfire_span("etape_chunking")
            chunks = self.chunk_documents(docs)
            if not chunks:
                logger.warning("❌ Aucun chunk créé")
                self._logfire_span("aucun_chunk_cree")
                return docs, [], []
            
            # Étape 4: Embeddings
            self._logfire_span("etape_embeddings")
            embeddings = self.generate_embeddings(chunks)
            
            logger.info("🎉 === PIPELINE TERMINÉ AVEC SUCCÈS ===")
            logger.info(f"📊 Résultats: {len(docs)} documents, {len(chunks)} chunks, {len(embeddings)} embeddings")
            self._logfire_span("pipeline_termine", 
                              documents=len(docs),
                              chunks=len(chunks), 
                              embeddings=len(embeddings))
            
            return docs, chunks, embeddings
            
        except Exception as e:
            logger.error(f"💥 ERREUR DANS LE PIPELINE: {e}")
            self._logfire_span("erreur_pipeline", error=str(e))
            raise


# --- Exemple d'exécution ---
if __name__ == "__main__":
    try:
        # Utilisez le même chemin que index.py
        from utils.config import INPUT_DIR
        
        # Debug du chemin
        input_path = Path(INPUT_DIR).absolute()
        print(f"📍 Chemin utilisé (identique à index.py): {input_path}")
        print(f"📍 Le dossier existe: {input_path.exists()}")
        
        if input_path.exists():
            files = list(input_path.iterdir())
            print(f"📄 Fichiers dans le dossier: {len(files)}")
            for f in files:
                if f.is_file():
                    print(f"  - {f.name} (taille: {f.stat().st_size} bytes)")
                else:
                    print(f"  - {f.name} [SOUS-DOSSIER]")
        
        # Pipeline avec paramètres optimisés
        pipeline = DataPipeline(chunk_size=500, chunk_overlap=50)
        docs, chunks, embeddings = pipeline.run(INPUT_DIR)
        
        print(f"\n" + "="*50)
        print("📊 RÉSULTATS DU PIPELINE")
        print("="*50)
        print(f"📄 Documents: {len(docs)}")
        print(f"✂️  Chunks: {len(chunks)}")
        print(f"🔢 Embeddings: {len(embeddings)}")
        
        if docs:
            print(f"\n📝 Exemple de document:")
            print(f"   ID: {docs[0].doc_id}")
            print(f"   Métadonnées: {docs[0].metadata}")
            print(f"   Texte (premieres 200 chars): {docs[0].text[:200]}...")
        
        if chunks:
            print(f"\n🧩 Exemple de chunk:")
            print(f"   ID: {chunks[0].chunk_id}")
            print(f"   Texte: {chunks[0].text[:100]}...")
        
        if embeddings:
            print(f"\n🔤 Exemple d'embedding:")
            print(f"   Chunk ID: {embeddings[0].chunk_id}")
            print(f"   Dimensions: {len(embeddings[0].vector)}")
            print(f"   Premières 5 valeurs: {embeddings[0].vector[:5]}")
            
    except ImportError:
        # Fallback si utils.config n'existe pas
        print("⚠️ utils.config non trouvé, utilisation du chemin par défaut 'inputs'")
        pipeline = DataPipeline(chunk_size=500, chunk_overlap=50)
        docs, chunks, embeddings = pipeline.run("inputs")
        
    except Exception as e:
        print(f"❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()

















