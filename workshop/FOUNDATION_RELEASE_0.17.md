# FOUNDATION RELEASE 0.17 — LOCAL AI MODEL BAY

Release 0.17 adds the Workshop's first real, optional local text-inference layer.

The Model Bay registers one official Liquid LFM2.5 1.2B Instruct Q4_K_M GGUF and one official llama.cpp Windows CPU runtime. It derives installed and READY states from exact local evidence, binds only to `127.0.0.1:8876`, uses fixed task routes, and has no cloud fallback.

Write gains one explicit Local AI Rewrite Assist path through the existing governed Worker Kit. It retains source IDs and hashes, an inspectable prompt-template version and parameters, separate plan and result approval, proposed output, inactive saving, export, receipts, recovery, and bounded rollback. The source is never overwritten.

The deterministic Workshop remains usable while Local AI is disabled or stopped. Auto-start is OFF. Release 0.17 does not add vision, speech, additional models, autonomous agents, arbitrary executables, arbitrary downloads, arbitrary URLs, or a general shell endpoint.

SQLite schema remains at `user_version=13`; no database replacement or migration is required.
