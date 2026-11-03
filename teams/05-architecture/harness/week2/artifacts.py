"""Strict tokenizer-v0 and G4 v2 raw-table integrity checks."""
from pathlib import Path
import hashlib
import json
import numpy as np
from tokenizers import Tokenizer

V0_SHA256 = "2de039f20d17afd17615095c406c43087359673b767ed0fe2c480b995f2af8e5"

def sha256(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for block in iter(lambda:f.read(1024*1024), b""):h.update(block)
    return h.hexdigest()

class Artifacts:
    def __init__(self, tokenizer_path, table_path, expected_tokenizer_sha=V0_SHA256, expected_vocab=131072):
        self.tokenizer_sha=sha256(tokenizer_path)
        if self.tokenizer_sha!=expected_tokenizer_sha:
            raise ValueError("Tokenizer identity mismatch: v0 must not silently become baseline/v0.1/v2")
        self.tokenizer=Tokenizer.from_file(str(tokenizer_path))
        self.tokenizer.no_padding();self.tokenizer.no_truncation()
        if self.tokenizer.get_vocab_size(with_added_tokens=True)!=expected_vocab:
            raise ValueError("Vocabulary mismatch")
        with np.load(table_path,allow_pickle=False) as z:
            if int(z["format_version"])!=2 or str(z["kind"])!="raw":
                raise ValueError("Expected Team 4 format-v2 RAW table, not decoded-token bytes")
            if str(z["tokenizer_sha256"])!=self.tokenizer_sha:
                raise ValueError("G4 table belongs to a different tokenizer: rebuild with G4 tool")
            self.bytes=z["bytes"].copy();self.lengths=z["lengths"].copy();self.pos_dim=int(z["pos_dim"])
            recorded=str(z["table_sha256"])
            if int(z["n_truncated"])!=0:raise ValueError("Truncated table cannot give exact heldout bytes")
        if self.bytes.dtype!=np.uint8 or self.lengths.dtype!=np.int16:
            raise ValueError("Invalid table dtype")
        if self.bytes.shape!=(expected_vocab,self.pos_dim) or self.lengths.shape!=(expected_vocab,):
            raise ValueError("Invalid table shape")
        if np.any(self.lengths<=0) or np.any(self.lengths>self.pos_dim):raise ValueError("Invalid byte lengths")
        h=hashlib.sha256(f"ke2-table-v2|raw|{self.pos_dim}|".encode())
        h.update(np.ascontiguousarray(self.bytes).tobytes());h.update(np.ascontiguousarray(self.lengths).tobytes())
        if h.hexdigest()!=recorded:raise ValueError("Table content hash mismatch")
        # Independently check all rows against the tokenizer JSON, not just sample text.
        spec=json.loads(Path(tokenizer_path).read_text(encoding="utf8"))
        alphabet=list(range(33,127))+list(range(161,173))+list(range(174,256))
        chars=alphabet.copy();extra=0
        for b in range(256):
            if b not in alphabet:alphabet.append(b);chars.append(256+extra);extra+=1
        inverse={chr(c):b for b,c in zip(alphabet,chars)}
        pieces={i:piece for piece,i in spec["model"]["vocab"].items()}
        added={a["id"]:a["content"] for a in spec.get("added_tokens",[])}
        for i in range(expected_vocab):
            expected=added[i].encode("utf8") if i in added else bytes(inverse[c] for c in pieces[i])
            actual=self.bytes[i,:int(self.lengths[i])].tobytes()
            if expected!=actual:raise ValueError(f"Raw table/tokenizer row mismatch at ID {i}")
        self.table_content_sha=recorded;self.table_file_sha=sha256(table_path)
        self.bos_id=self.tokenizer.token_to_id("<|begin_of_text|>")
        self.pad_id=self.tokenizer.token_to_id("<|pad|>")
        if self.bos_id is None or self.pad_id is None:raise ValueError("Missing actual BOS/PAD IDs")

    def encode(self,text):
        if not isinstance(text,str):raise ValueError("Expected a text string")
        ids=self.tokenizer.encode(text,add_special_tokens=False).ids
        raw=b"".join(self.bytes[i,:int(self.lengths[i])].tobytes() for i in ids)
        if raw!=text.encode("utf8"):
            raise ValueError("Tokenizer/table does not exactly reconstruct source UTF-8; BPB would be invalid")
        return ids

    def identity(self):
        return dict(tokenizer_sha256=self.tokenizer_sha,table_file_sha256=self.table_file_sha,
                    table_content_sha256=self.table_content_sha,vocab_size=len(self.lengths),
                    pos_dim=self.pos_dim,bos_id=self.bos_id,pad_id=self.pad_id)
