# Open Untethered AIOS in Codex — Windows

Use a NEW local folder and a NEW Codex chat for Untethered AIOS.

Do not open this as a subfolder/repo inside the authoritative Workshop.

## 1. Put the repos beside each other

Recommended layout:

```text
C:\TWIS_FLASHRIVER_REVIEW_READY\
├── TWIS\
└── Untethered-AIOS\
```

`TWIS` stays the authoritative production Workshop.

`Untethered-AIOS` is the experimental repo Codex may edit.

## 2. Clone Untethered AIOS

Open PowerShell and run:

```powershell
cd C:\TWIS_FLASHRIVER_REVIEW_READY
git clone https://github.com/Karmicmurphy/Untethered-AIOS.git Untethered-AIOS
cd .\Untethered-AIOS
```

If that folder already exists because you cloned it earlier, do not clone again. Instead:

```powershell
cd C:\TWIS_FLASHRIVER_REVIEW_READY\Untethered-AIOS
git pull
```

## 3. Open the new repo in Codex

In the ChatGPT desktop app on Windows:

1. Select **Codex** from the top-left menu.
2. Open the local folder/repository:
   `C:\TWIS_FLASHRIVER_REVIEW_READY\Untethered-AIOS`
3. Make sure Untethered AIOS — NOT `TWIS` — is the active working folder.
4. Select **New chat** for a fresh Codex coding thread.

The old Workshop Codex thread can remain where it is for production Workshop work.

## 4. Give Codex one message

Paste this as the first message:

> Read `AGENTS.md` and `CODEX_START_HERE.md` completely. This is the new Untethered AIOS repository. The authoritative Workshop is `C:\TWIS_FLASHRIVER_REVIEW_READY\TWIS` and must remain read-only. Execute Phase 0 exactly and authenticate/import the current code-safe Workshop baseline into this repo on a candidate branch. Then execute the mandatory Phase 0.5 updated Artifact Compass sweep using `skills/artifact-compass`, `skills/deep-salvage` when useful, and the supporting No-Drift/Direct-Successor/No-Broadening/evidence skills. Classify serious technologies `KEEP/CUT/TEST/REJECT/DEFER`, salvage mechanisms rather than whole platforms, stay free-first/local-first/legal-aware/hardware-measured, and end with one bounded Kernel V0.2 implementation decision. Continue automatically into KERNEL V0.2. Do not restart already-deployed Music Loop Deck V1. Fix ordinary candidate defects automatically. Stop only at a real protected/live deployment gate.

That is enough. Do not paste the entire old Music handoff again unless Codex proves it needs specific historical evidence.

## 5. Permission prompt

Codex may need permission to READ files outside the Untethered repo because the authoritative Workshop is a sibling folder.

Allow the minimum access required to inspect/read:

`C:\TWIS_FLASHRIVER_REVIEW_READY\TWIS`

Do not authorize Codex to modify the live Workshop as part of this AIOS program.

## 6. What Codex should do automatically

Codex should:

1. create `bootstrap/workshop-baseline` from Untethered `main`;
2. authenticate the real Workshop;
3. inspect exclusions;
4. verify source health;
5. import the code-safe baseline into `workshop/`;
6. prove hashes match;
7. run Untethered tests;
8. run the mandatory Artifact Compass bounded reality sweep;
9. classify findings `KEEP/CUT/TEST/REJECT/DEFER` and choose one bounded implementation;
10. continue into KERNEL V0.2 using Direct Successor Autopilot + NDBA;
11. fix ordinary candidate defects;
12. run No-Broadening Audit;
13. record receipt/trace/certificate evidence;
14. stop before any live Workshop modification/deployment.

If Codex begins rebuilding Music Loop Deck V1, rewriting the Workshop, installing giant models, broadening into Rust/WASM/vector DB/provider work without current evidence, or editing the authoritative `TWIS` folder, stop that thread and point it back to `CODEX_START_HERE.md`.
