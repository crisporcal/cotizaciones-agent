from sentence_transformers import SentenceTransformer
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import pickle, os

class SimpleVectorStore:
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        self.model = SentenceTransformer(model_name)
        self.docs = []
        self.embeddings = None

    def add_documents(self, docs: list):
        texts = [d['text'] for d in docs]
        embs = self.model.encode(texts, show_progress_bar=False)
        if self.embeddings is None:
            self.embeddings = np.array(embs)
        else:
            self.embeddings = np.vstack([self.embeddings, embs])
        self.docs.extend(docs)

    def query(self, text: str, k: int = 3):
        if self.embeddings is None or len(self.docs) == 0:
            return []
        q_emb = self.model.encode([text], show_progress_bar=False)[0]
        sims = cosine_similarity([q_emb], self.embeddings)[0]
        idxs = np.argsort(sims)[::-1][:k]
        results = []
        for i in idxs:
            results.append({'score': float(sims[i]), 'doc': self.docs[i]})
        return results

    def save(self, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        payload = {'docs': self.docs, 'embeddings': self.embeddings}
        with open(path, 'wb') as f:
            pickle.dump(payload, f)

    def load(self, path: str):
        with open(path, 'rb') as f:
            payload = pickle.load(f)
        self.docs = payload['docs']
        self.embeddings = payload['embeddings']
