# Input, Attach & Voice — Wired Summary

**Purpose:** Single reference for what’s on every main input (chat box): microphone, attach, and supported file types.

---

## Where the input bar appears

| Page | Has input bar | Mic (voice) | Paperclip (attach) | Notes |
|------|----------------|-------------|--------------------|--------|
| **Landing** | ✅ Hero + CTA | ✅ Record → transcribe via API | ✅ | accept: 12+ types; audio transcribed on submit |
| **Our Projects** | ✅ | ✅ Same as Landing | ✅ | Same accept; audio transcribed on submit |
| **Dashboard** | ✅ Home prompt | ✅ Record → transcribe via API | ✅ | accept: 12+ types; audio transcribed on submit |
| **Workspace** | ✅ Chat at bottom | ✅ Web Speech API (live) | ✅ | ZIP in attach parses into workspace; audio transcribed on submit |

---

## Supported file types (unified)

All main input areas accept:

- **Images:** `image/*` (screenshots, mockups, design-to-code)
- **Documents:** `.pdf`, `.txt`, `.md`
- **Code:** `.js`, `.jsx`, `.ts`, `.tsx`, `.css`, `.html`, `.json`, `.py`
- **Archive:** `.zip` (Workspace: parsed and loaded into editor; others: sent with request)
- **Voice notes:** `audio/*` (transcribed via `/api/voice/transcribe` and appended to prompt on submit)

So users can: type, use the **microphone** (record or attach audio), or **attach** images, PDFs, text, code files, ZIP, and voice notes.

---

## Behavior

1. **Microphone (live record)**  
   - Landing, Our Projects, Dashboard: record in browser → stop → send to `/api/voice/transcribe` → text inserted into prompt.  
   - Workspace: Web Speech API (no server call for live mic).

2. **Attached audio (voice note)**  
   - On submit, any attached `audio/*` files are sent to `/api/voice/transcribe`; returned text is appended to the prompt; audio is not sent as a separate attachment to the build/chat.

3. **Attached ZIP**  
   - **Workspace:** Parser runs in the client; code files from the ZIP are loaded into the workspace (same as “Upload ZIP” in Explorer).  
   - Dashboard/Landing/Our Projects: ZIP is included in the request (e.g. for import flows).

4. **Icons**  
   - Attached files: image → Image icon, audio → Mic icon, other → FileText icon (Landing, Our Projects, Workspace).

---

## Verification (code)

- **Workspace:** `handleFileSelect` supports zip (JSZip parse → `setFiles`), audio (transcribe in `handleBuild`), and expanded `accept`. Mic + Paperclip in the chat bar.
- **Dashboard:** `handleFileSelect` supports zip (readAsArrayBuffer → base64) and audio (readAsDataURL); `handleSubmit` transcribes audio then continues. Mic (VoiceWaveform/startRecording) + Paperclip; `accept` includes `.zip`, `audio/*`, and code extensions.
- **LandingPage:** `handleLandingFileSelect` supports zip and audio; `handleSubmit` transcribes audio then `startBuild`. Mic + Paperclip; `accept` expanded.
- **OurProjectsPage:** Same as Landing (handleLandingFileSelect + handleSubmit); Mic + Paperclip; `accept` expanded.

---

*All main CrucibAI input surfaces now have microphone, attach, and 12+ file types (including ZIP and voice notes) wired and consistent.*
