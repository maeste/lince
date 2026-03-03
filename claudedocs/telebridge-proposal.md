# Telebridge: Telegram Bridge per LINCE

**Data**: 2026-03-03
**Stato**: Proposta / RFC
**Autore**: Analisi collaborativa

---

## Sommario Esecutivo

Questa proposta analizza l'aggiunta di un modulo **Telegram bridge** al progetto LINCE, permettendo il controllo remoto di Claude Code tramite messaggi Telegram. Vengono valutate tre opzioni di implementazione, con raccomandazione motivata per l'Opzione C (nuovo modulo nativo). La proposta include anche il supporto messaggi vocali Telegram tramite riuso del motore di trascrizione di VoxCode.

---

## Contesto

### Il problema

LINCE oggi richiede accesso diretto al terminale. Non esiste modo di interagire con Claude Code da remoto (es. dal telefono) senza SSH o VNC. Un bridge Telegram risolverebbe questo permettendo:

- Mandare prompt a Claude Code da Telegram
- Ricevere risposte formattate su Telegram
- Interagire con le UI interattive di Claude Code (permessi, scelte) tramite bottoni inline
- Inviare messaggi vocali Telegram come input testuale (tramite trascrizione)

### Progetto di riferimento: ccbot

[ccbot](https://github.com/six-ddc/ccbot) (MIT license, 127 stelle, 16 contributor, attivamente sviluppato a marzo 2026) implementa esattamente questo bridge. L'analisi che segue si basa su un'ispezione approfondita del suo codice sorgente e architettura.

---

## Analisi tecnica di ccbot

### Architettura

```
Telegram User (mobile/desktop)
        |
        v
[python-telegram-bot]          -- polling mode
        |
        v
[bot.py]                       -- command/message router (71KB, monolite)
        |
        +---> [SessionManager] -- mappa Telegram topics <-> tmux windows
        |         |
        |         v
        |     [TmuxManager]    -- send_keys() al pane Claude Code (libtmux)
        |         |
        |         v
        |     [tmux window]    -- processo `claude` CLI attivo
        |
        +---> [SessionMonitor] -- polling file JSONL transcript
                  |
                  v
              [TranscriptParser] -- parsing output Claude Code
                  |
                  v
              [ResponseBuilder]  -- formattazione per Telegram (split 4096 char)
                  |
                  v
              [TelegramSender]   -- invio messaggi al topic dell'utente
```

### Feature principali

| Feature | Dettaglio |
|---------|-----------|
| **Sessioni** | 1 topic Telegram = 1 sessione Claude Code, con resume |
| **Output real-time** | Polling JSONL ogni 2s, offset incrementale con recovery |
| **UI interattive** | Permessi, scelte, checkpoint renderizzati come tastiere inline |
| **Screenshot** | Cattura terminale come PNG con colori ANSI e font CJK |
| **Voice-to-text** | Trascrizione via API OpenAI (cloud, non locale) |
| **Immagini** | Invio foto da Telegram a Claude Code |
| **Directory browser** | Navigazione filesystem per scegliere working directory |
| **Comandi** | /history, /screenshot, /esc, /usage, /model e altri |

### Dipendenze

| Componente | Versione | Scopo |
|------------|----------|-------|
| python-telegram-bot | >=21.0 | API Telegram |
| libtmux | >=0.37.0 | Controllo tmux da Python |
| Pillow | >=10.0.0 | Screenshot terminale |
| aiofiles | >=24.0.0 | I/O asincrono |
| telegramify-markdown | >=0.5.0 | Markdown -> MarkdownV2 |
| Python | 3.12+ | Runtime |

### Punti di forza

- Feature-complete e collaudato in produzione
- Architettura a hook (SessionStart) per binding automatico sessioni
- Parsing JSONL robusto con recovery da corruzione e offset tracking
- Bridging UI interattive ben progettato
- MIT license, nessuna restrizione di riuso
- Community attiva (48 fork in un mese)

### Punti critici

1. **Accoppiamento stretto a tmux**: `libtmux` usato direttamente ovunque, nessuna astrazione
2. **Monolite**: `bot.py` da 71KB, single file con tutta la logica di routing
3. **Python 3.12+**: LINCE supporta 3.11+
4. **Voice cloud-only**: Usa API OpenAI per trascrizione, non locale come VoxCode
5. **Nessun supporto Zellij**: Zero astrazione multiplexer
6. **Timing fragile**: `send_keys()` con delay hardcoded (500ms prima di Enter)

---

## Analisi di compatibilita con LINCE

### Architettura LINCE attuale

LINCE e un toolkit modulare con componenti indipendenti:

```
lince/
 ├── sandbox/          -- Sandbox Bubblewrap per Claude Code
 ├── voxcode/          -- Input vocale locale (Whisper)
 ├── zellij-setup/     -- Layout Zellij 3 pane
 ├── agent-ready-skill/-- Assessment readiness agentica
 └── backlog/          -- Task tracking Backlog.md
```

### Pattern architetturali LINCE

| Pattern | Implementazione |
|---------|----------------|
| **Multiplexer abstraction** | `MultiplexerBridge` protocol con `TmuxBridge` e `ZellijBridge` |
| **Config-driven** | TOML config con default sensati |
| **Auto-detection** | Rileva tmux/Zellij da variabili d'ambiente |
| **Single-responsibility** | File piccoli, un concern per modulo |
| **Entry points** | CLI via `pyproject.toml` `[project.scripts]` |
| **Package management** | uv |

### Gap da colmare

ccbot non ha nessuno di questi pattern. L'integrazione diretta richiederebbe adattare ccbot ai pattern LINCE oppure accettare un'incoerenza architetturale significativa.

---

## Le tre opzioni

### Opzione A: Integrare ccbot come dipendenza esterna

**Approccio**: Installare ccbot separatamente e usarlo accanto a LINCE.

**Pro**:
- Zero effort di sviluppo
- Si beneficia degli aggiornamenti upstream

**Contro**:
- Rompe la compatibilita Zellij (ccbot e solo tmux)
- Incoerenza architetturale (monolite vs modulare, hatchling vs uv)
- Duplicazione: ccbot ha il suo voice-to-text (cloud), VoxCode ha il suo (locale)
- Nessuna integrazione con la sandbox
- Esperienza utente frammentata (due tool separati da configurare)
- Python 3.12+ vs 3.11+ di LINCE

**Effort stimato**: Basso (configurazione)
**Debito tecnico**: Alto (incoerenza permanente)

**Verdetto**: Sconsigliata. Risolve il problema nell'immediato ma crea frammentazione permanente.

### Opzione B: Fork e adattare ccbot

**Approccio**: Forkare ccbot, refactorare per Zellij e integrare nel monorepo.

**Pro**:
- Si parte da codice funzionante e collaudato
- Feature-complete dal giorno zero
- Si puo contribuire upstream con i miglioramenti

**Contro**:
- **40-50% del codice da riscrivere** per il supporto Zellij:
  - `tmux_manager.py` -- riscrittura completa
  - `hook.py` -- adattamento query tmux
  - `session.py` -- modello stato basato su window ID tmux
  - `bot.py` (71KB) -- riferimenti tmux sparsi ovunque
  - `screenshot.py` -- cattura pane tmux-specifica
  - `interactive_ui.py` -- lettura pane tmux
- Scomposizione necessaria di `bot.py` (71KB monolite)
- Divergenza dall'upstream rende merge futuri difficili
- Voice-to-text cloud (OpenAI API) da sostituire con Whisper locale
- Tempo di comprensione del codice altrui prima di poter modificare

**Effort stimato**: Alto (refactoring estensivo + testing)
**Debito tecnico**: Medio (si eredita architettura non nostra)

**Verdetto**: Possibile ma costosa. Il refactoring necessario e cosi esteso da avvicinarsi allo sforzo di una riscrittura, ma con il vincolo aggiuntivo di lavorare dentro un'architettura non progettata per i nostri requisiti.

### Opzione C: Nuovo modulo `telebridge/` ispirato a ccbot (Raccomandata)

**Approccio**: Creare un modulo nativo LINCE che riusa le idee architetturali di ccbot ma segue i pattern del progetto.

**Pro**:
- **Coerenza architetturale**: stessi pattern di VoxCode (config TOML, MultiplexerBridge, uv)
- **Zellij-first con tmux fallback**: riusa l'astrazione multiplexer gia collaudata
- **Riuso componenti VoxCode**: trascrizione locale Whisper per messaggi vocali
- **Nessun debito tecnico ereditato**: codice nostro, architettura nostra
- **Sviluppo incrementale**: MVP send/receive, poi feature avanzate
- **Manutenibilita**: codice modulare, facile da estendere e debuggare
- **Singolo stack**: uv, Python 3.11+, TOML config, tutto coerente

**Contro**:
- Piu lavoro iniziale rispetto a un fork
- Bisogna reimplementare i pattern di ccbot (JSONL monitoring, hook system, response formatting)
- Rischio di reintrodurre bug gia risolti in ccbot

**Mitigazione dei contro**:
- ccbot resta come **riferimento architetturale** -- non si reimplementa da zero, si reimplementano pattern noti
- Le innovazioni core di ccbot (JSONL monitoring, hook binding) sono concettualmente semplici
- Il codice tmux-specifico (che e il grosso di ccbot) non ci serve: lo sostituiamo con MultiplexerBridge

**Effort stimato**: Medio (implementazione guidata da pattern noti)
**Debito tecnico**: Basso (architettura nativa)

**Verdetto**: Raccomandata. Massima coerenza, minimo debito tecnico, percorso incrementale chiaro.

---

## Perche l'Opzione C e la scelta migliore

### 1. L'accoppiamento tmux di ccbot e strutturale, non superficiale

Il problema non e "ccbot usa tmux" ma "ccbot e costruito *attorno* a tmux". La libreria `libtmux` non e chiamata in un punto solo: permea `tmux_manager.py`, `hook.py`, `session.py`, `bot.py`, `screenshot.py`, `interactive_ui.py`. Non esiste un'interfaccia da sostituire -- bisogna riscrivere la logica di 6+ file.

Per un fork (Opzione B), questo significa che il refactoring necessario tocca il 40-50% del codice. A quel punto, il vantaggio di "partire da codice funzionante" si riduce significativamente.

### 2. LINCE ha gia l'astrazione che ccbot non ha

VoxCode implementa `MultiplexerBridge` con backend per Zellij e tmux. Questo protocol va solo esteso con:

```python
class MultiplexerBridge(Protocol):
    # Gia esistenti:
    def validate(self) -> None: ...
    def get_target_pane(self) -> str: ...
    def send_text(self, text: str) -> None: ...

    # Da aggiungere per telebridge:
    def capture_pane(self) -> str: ...
    def send_keys(self, keys: list[str]) -> None: ...
```

Per Zellij:
- `capture_pane()` -> `zellij action dump-screen`
- `send_keys()` -> `zellij action write` (byte codes per tasti speciali)

Per tmux:
- `capture_pane()` -> `tmux capture-pane -p`
- `send_keys()` -> `tmux send-keys`

Questo riuso e impossibile con un fork di ccbot senza riscrivere comunque la stessa quantita di codice.

### 3. La trascrizione vocale e gia risolta localmente

ccbot usa l'API OpenAI per voice-to-text (cloud, a pagamento, richiede API key). VoxCode ha gia:

- `Transcriber` -- wrapper faster-whisper con lazy loading, supporto GPU
- Modelli fino a large-v3, trascrizione locale, zero costi API
- VAD (Voice Activity Detection) energy-based

Per il bridge Telegram, il flusso vocale diventa:

```
Messaggio vocale Telegram (OGG/Opus)
    |
    v
Download file via Telegram API
    |
    v
Conversione OGG -> WAV 16kHz mono (ffmpeg o pydub)
    |
    v
VoxCode Transcriber.transcribe(audio_array)
    |
    v
Testo trascritto -> send_text() al pane Claude Code
```

Con l'Opzione C, questo riuso e naturale: si importa `Transcriber` da voxcode.
Con l'Opzione B, bisognerebbe prima rimuovere la dipendenza OpenAI di ccbot e poi integrare VoxCode, con due codebase che non condividono pattern.

### 4. Lo sviluppo incrementale e piu sicuro

L'Opzione C permette un percorso MVP chiaro:

| Fase | Feature | Complessita |
|------|---------|-------------|
| **MVP** | Send prompt + receive response via Telegram | Bassa |
| **v0.2** | Sessioni multiple (1 topic = 1 sessione) | Media |
| **v0.3** | UI interattive (permessi, scelte) via inline keyboard | Media |
| **v0.4** | Screenshot terminale | Media |
| **v0.5** | Messaggi vocali Telegram (riuso VoxCode Transcriber) | Bassa |
| **v0.6** | Invio immagini da Telegram a Claude Code | Bassa |

Ogni fase e autonoma, testabile e rilasciabile. Con un fork, si eredita tutto in blocco e bisogna garantire che tutto funzioni dopo il refactoring.

### 5. Tabella comparativa sintetica

| Criterio | A: Dipendenza | B: Fork | C: Nuovo modulo |
|----------|:---:|:---:|:---:|
| Compatibilita Zellij | No | Si (dopo refactor) | Si (nativo) |
| Coerenza architetturale | Bassa | Media | Alta |
| Voice locale (Whisper) | No (cloud) | Da integrare | Riuso VoxCode |
| Integrazione sandbox | No | Da fare | Nativa |
| Effort iniziale | Basso | Alto | Medio |
| Debito tecnico | Alto | Medio | Basso |
| Manutenibilita | Bassa | Media | Alta |
| Percorso incrementale | No | No | Si |
| Aggiornamenti upstream | Si | Divergenza | N/A (riferimento) |

---

## Architettura proposta per `telebridge/`

### Struttura del modulo

```
telebridge/
├── src/telebridge/
│   ├── __main__.py              # Entry point
│   ├── cli.py                   # Argparse, config loading, bootstrap
│   ├── config.py                # TOML config + .env per secrets
│   ├── bot.py                   # Telegram Application setup, handler registration
│   ├── handlers/
│   │   ├── messages.py          # Text message -> Claude Code
│   │   ├── commands.py          # /start, /screenshot, /history, /esc
│   │   ├── callbacks.py         # Inline keyboard callbacks (UI interattive)
│   │   ├── voice.py             # Messaggi vocali -> Transcriber -> Claude Code
│   │   └── media.py             # Immagini e altri media
│   ├── session_monitor.py       # JSONL polling con offset tracking
│   ├── transcript_parser.py     # Parser output Claude Code
│   ├── response_formatter.py    # Markdown -> Telegram MarkdownV2, split 4096
│   ├── interactive_ui.py        # Cattura pane -> inline keyboard
│   ├── screenshot.py            # Terminale -> PNG (Pillow)
│   ├── hook.py                  # Installer hook SessionStart Claude Code
│   └── session_manager.py       # Mapping topic <-> pane <-> session
├── pyproject.toml
├── config.example.toml
└── README.md
```

### Dipendenze condivise con VoxCode

```
telebridge dipende da:
├── voxcode.transcriber.Transcriber    # Trascrizione Whisper locale
├── voxcode.multiplexer.MultiplexerBridge  # Astrazione tmux/Zellij
├── voxcode.multiplexer.create_bridge  # Factory multiplexer
└── (estensioni al protocol MultiplexerBridge)
```

**Nota**: Questa dipendenza puo essere gestita in due modi:

1. **Import diretto** (`from voxcode.transcriber import Transcriber`): semplice, VoxCode e una dipendenza di telebridge
2. **Libreria condivisa** (`lince-core`): estrarre `Transcriber` e `MultiplexerBridge` in un pacchetto base comune

L'opzione 1 e sufficiente per l'MVP. L'opzione 2 va valutata se emergono ulteriori moduli che necessitano gli stessi componenti.

### Flusso dati

```
                    TELEGRAM
                       |
        +--------------+--------------+
        |              |              |
    Testo          Vocale         Immagine
        |              |              |
        v              v              v
   handlers/      handlers/      handlers/
   messages.py    voice.py       media.py
        |              |              |
        |         Transcriber         |
        |         (VoxCode)           |
        |              |              |
        +--------------+--------------+
                       |
                       v
              MultiplexerBridge
              .send_text(prompt)
                       |
              +--------+--------+
              |                 |
         ZellijBridge      TmuxBridge
              |                 |
              v                 v
         Claude Code CLI (in sandbox)
              |
              v
         JSONL transcript files
              |
              v
         SessionMonitor (polling)
              |
              v
         TranscriptParser
              |
              v
         ResponseFormatter
              |
              v
         Telegram API -> utente
```

### Integrazione messaggi vocali (dettaglio)

Il flusso per un messaggio vocale Telegram:

```python
# handlers/voice.py (pseudocodice)

async def handle_voice(update, context):
    # 1. Download file vocale da Telegram
    voice_file = await update.message.voice.get_file()
    ogg_bytes = await voice_file.download_as_bytearray()

    # 2. Conversione OGG/Opus -> numpy array float32 16kHz
    audio_array = await convert_ogg_to_array(ogg_bytes)

    # 3. Trascrizione via VoxCode Transcriber (locale, GPU)
    transcriber = get_transcriber()  # singleton, lazy-loaded
    result = transcriber.transcribe(audio_array, language=config.language)

    # 4. Invio testo trascritto al pane Claude Code
    bridge = get_bridge()  # MultiplexerBridge
    bridge.send_text(result.text)

    # 5. Conferma all'utente
    await update.message.reply_text(f"Trascritto: {result.text}")
```

**Componenti riusati da VoxCode**:
- `Transcriber` -- gia gestisce lazy loading, GPU/CPU, modelli multipli
- Non serve `AudioCapture` ne `EnergyVAD` (il file vocale Telegram e gia segmentato)

**Componente nuovo necessario**:
- Conversione OGG/Opus -> numpy array (poche righe con `ffmpeg` subprocess o `pydub`)

### Configurazione

```toml
# config.example.toml

[telegram]
# Bot token da @BotFather (oppure in .env come TELEGRAM_BOT_TOKEN)
# bot_token = ""
allowed_users = []          # Lista Telegram user ID autorizzati

[session]
poll_interval = 2.0         # Secondi tra polling JSONL
auto_bind = true            # Binding automatico topic <-> sessione

[voice]
enabled = true
language = "auto"           # Lingua trascrizione (auto, it, en, ...)
whisper_model = "large-v3"  # Modello Whisper
whisper_device = "cuda"     # cuda o cpu
whisper_compute = "float16"

[multiplexer]
backend = "auto"            # auto, tmux, zellij
send_enter = true

[zellij]
target_pane = "up"          # Direzione del pane Claude Code

[tmux]
target_pane = ""            # Auto-detect pane Claude Code
```

---

## Rischi e mitigazioni

| Rischio | Impatto | Probabilita | Mitigazione |
|---------|---------|-------------|-------------|
| `dump-screen` Zellij meno maturo di `capture-pane` tmux | Screenshot/UI interattive degradate su Zellij | Media | Test approfonditi; fallback a output solo testo |
| Latenza polling JSONL (2s) | Risposta non immediata | Bassa | `inotify` come alternativa per Linux; poll interval configurabile |
| Token Telegram esposto in ambiente | Sicurezza | Media | Scrubbing env come ccbot; integrazione sandbox |
| Whisper GPU non disponibile | Trascrizione vocale lenta | Bassa | Fallback CPU; modello configurabile (tiny -> large-v3) |
| Conversione OGG -> WAV richiede ffmpeg | Dipendenza sistema aggiuntiva | Bassa | ffmpeg e quasi universale su Linux; documentare requisito |
| Drift architetturale da ccbot senza beneficio | Feature mancanti | Bassa | Mantenere ccbot come riferimento, implementare per fasi |

---

## Roadmap proposta

### Fase 1 -- MVP (send/receive)
- Bot Telegram base con python-telegram-bot
- Invio testo -> MultiplexerBridge -> Claude Code
- JSONL monitoring -> risposta formattata su Telegram
- Config TOML + .env
- Supporto Zellij e tmux

### Fase 2 -- Sessioni
- 1 topic Telegram = 1 sessione Claude Code
- Hook SessionStart per binding automatico
- Resume sessioni esistenti
- Comandi /start, /esc, /unbind

### Fase 3 -- UI interattive
- Cattura pane (capture_pane via MultiplexerBridge)
- Rendering permessi/scelte come inline keyboard
- Navigazione con bottoni (frecce, Enter, Esc)

### Fase 4 -- Media
- Screenshot terminale (Pillow)
- Invio immagini da Telegram a Claude Code

### Fase 5 -- Voice
- Download messaggi vocali Telegram
- Conversione OGG -> array audio
- Trascrizione locale via VoxCode Transcriber
- Invio testo trascritto a Claude Code

### Fase 6 -- Polish
- Directory browser per working directory
- Cronologia messaggi paginata (/history)
- Statistiche token/costo (/usage)
- Documentazione completa

---

## Conclusione

L'Opzione C (nuovo modulo `telebridge/`) e la scelta raccomandata perche:

1. **Mantiene la coerenza architetturale** di LINCE (Zellij-first, modulare, TOML config)
2. **Riusa componenti esistenti** (MultiplexerBridge, Transcriber) senza duplicazione
3. **Non introduce debito tecnico** da un fork con refactoring estensivo
4. **Permette sviluppo incrementale** con MVP rilasciabile in tempi brevi
5. **Risolve il voice-to-text** con trascrizione locale invece che cloud
6. **ccbot resta come riferimento** per i pattern architetturali, non come codice da mantenere

Il risultato finale sara un modulo che si integra naturalmente nell'ecosistema LINCE come VoxCode, sandbox e gli altri componenti.
