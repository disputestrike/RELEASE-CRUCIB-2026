# Import `work` branch from Codex Base64 parts

**Blocker for fifty-point #47:** This repo cannot supply **PART 001–003** for you. Only the original Codex/chat paste contains those blocks. After you add `bundle_parts_001_003.txt`, the rest is mechanical (decode → `git fetch` bundle).

## What is in this repo

| File | Contents |
|------|-----------|
| `bundle_parts_004_006.txt` | **PART 004, 005, 006** (from your ChatGPT paste) — already placed here. |
| `bundle_parts_001_003.txt` | **You must create this** — paste PART 001–003 from your **first** Base64 message (the one that starts the bundle). |

**Important:** Decoding **only** parts 4–6 produces a tiny invalid file (~18 KB). You **must** merge with parts **001–003** to get the full ~9–10 MB bundle.

## Steps

### 1) Create `handoff/bundle_parts_001_003.txt`

Paste **only** the blocks `---BEGIN PART 001---` … `---END PART 003---` from your earlier chat (same format as parts 4–6).

### 2) Decode (script sorts part numbers from all files)

From repo root:

```powershell
cd C:\Users\benxp\OneDrive\Desktop\CRUCIBAI2026\crucib
python scripts\decode_bundle_parts.py handoff\bundle_parts_001_003.txt handoff\bundle_parts_004_006.txt crucibai-work.bundle
```

If you put everything in one file instead:

```powershell
python scripts\decode_bundle_parts.py handoff\bundle_parts_ALL.txt crucibai-work.bundle
```

### 3) Verify and import

```powershell
git bundle verify crucibai-work.bundle
git fetch crucibai-work.bundle work:refs/heads/work-from-bundle
git checkout -B work work-from-bundle
git rev-parse HEAD
```

Expect: `ba63286f75568abc70a51d0ca825aebb843681b6` (or same short `ba63286`).

### 4) Push from your PC

```powershell
git push -u crucibai work
```

## Expected size

Decoded file should be on the order of **9–10 MB**. Much smaller means missing parts or truncation.

## Expected SHA-256 (from Codex server)

`e2f7e78b2394b1b7bfe9bc9fd06176744d99ec41fbab766de324e477e94f8868`

(Will only match if your paste is complete and unmodified.)
