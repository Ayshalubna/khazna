import os

os.environ.setdefault("KHAZNA_DB", "/tmp/khazna_test_audit.db")
os.environ.setdefault("KHAZNA_WARMUP", "0")          # tests control the egress guard themselves
os.environ.setdefault("KHAZNA_READS_PER_MIN", "10000")
os.environ.setdefault("KHAZNA_WRITES_PER_MIN", "10000")
