# French translation proposal

Status: French copy approved, with **ASTRA — LAST LIGHT** kept in English.
Runtime and offline-generator integration is implemented in this workspace;
host validation is pending below. Native visual, memory and performance
acceptance remain pending. The post-intro selector remembers French/English for
the running session, including death, return to title and replay.

## Direction

Keep **ASTRA — LAST LIGHT** and the ACE/Micrix branding unchanged in both
languages. Narrative references to the last light may still use **la dernière
lueur**; they are not the game title. Use concise, cinematic French: collective resolve in dialogue,
direct instructions in the UI. Preserve accented capitals. Keep pickup letters
D/F/S/R/L unchanged: they are gameplay symbols tied to existing assets and rules.

This inventory is implemented in `game/art/localization.json`: UI, sector entry
names, all thirteen scenes and offline HUD/ending labels. `logic.c` retains its
historical English sector names for non-rendering consumers; rendering uses the
catalog. Diagnostic serial output remains stable.

## Language screen and interface

The selector uses **FRANÇAIS** and **ENGLISH**, matching SuperRugbyV. No extra
instruction line is proposed for that screen, to preserve the reference layout.

| English | Proposed French |
|---|---|
| ASTRA | ASTRA |
| LAST LIGHT | LAST LIGHT |
| FIRE TO DEFEND THE DAWN | FEU POUR DÉFENDRE L’AUBE |
| OR | OU |
| TO CHANGE SECTOR | CHANGER DE SECTEUR |
| GAME OVER | FIN DE PARTIE |
| THE FLEET WILL REMEMBER YOU | LA FLOTTE SE SOUVIENDRA DE VOUS |
| RETURNING TO TITLE | RETOUR AU TITRE |
| FIRE TO RESTART | FEU POUR REJOUER |
| SCORE | SCORE |
| LIVES | VIES |
| SECTOR | SECTEUR |
| LANCE | LANCE |
| READY | PRÊT |
| DAMAGE | DÉGÂTS |
| SPEED | VIT. |
| SHIELD | BOUCL. |
| FIRE | TIR |
| HOLD TO CHARGE | MAINTENIR LE TIR |
| RELEASE FIRE | RELÂCHER LE TIR |
| BOSS | BOSS |
| PAUSE | PAUSE |

**VIT.** and **BOUCL.** abbreviate VITESSE and BOUCLIER to protect the compact HUD.
Use **FEU** for the controller action and **TIR** for the weapon/status label.
All translations still require pixel-fit validation, including the enlarged
game-over heading; centering English coordinates is insufficient. The unchanged
English game title retains its existing layout.

## Campaign: full authored text

Sector names are the entry titles for scenes 0, 3, 6 and 9. Each scene below
lists title, caption and reply in source order.

### 0 — Sector 1 arrival

| English | French |
|---|---|
| ORBITAL GRAVEYARD | CIMETIÈRE ORBITAL |
| THE WRECKS STILL CALL OUR NAMES | LES ÉPAVES NOUS APPELLENT ENCORE |
| KEEP THE LAST LIGHT ALIVE | PRÉSERVONS LA DERNIÈRE LUEUR |

### 1 — Sector 1 boss

| English | French |
|---|---|
| SALVAGE CLAW | LA GRIFFE RÉCUPÉRATRICE |
| A REACTOR WAKES AMONG THE DEAD | UN RÉACTEUR S’ÉVEILLE PARMI LES MORTS |
| THOSE JAWS WILL NOT TAKE US | SES MÂCHOIRES NE NOUS AURONT PAS |

### 2 — Sector 1 victory

| English | French |
|---|---|
| WRECK FIELD FREED | CHAMP D’ÉPAVES LIBÉRÉ |
| THE CLAW FALLS SILENT | LA GRIFFE SE TAIT |
| SET COURSE FOR THE VEIL | CAP SUR LE VOILE |

### 3 — Sector 2 arrival

| English | French |
|---|---|
| VEIL NEBULA | NÉBULEUSE DU VOILE |
| SOMETHING MOVES IN THE CLOUDS | QUELQUE CHOSE BOUGE DANS LES NUAGES |
| FOLLOW THE SIGNAL THROUGH | SUIVONS LE SIGNAL |

### 4 — Sector 2 boss

| English | French |
|---|---|
| THE MANTA WAKES | LA MANTA S’ÉVEILLE |
| THAT SHADOW IS ALIVE | CETTE OMBRE EST VIVANTE |
| WATCH THE FINS AND HOLD FAST | SURVEILLEZ SES AILERONS ET TENEZ BON |

### 5 — Sector 2 victory

| English | French |
|---|---|
| VEIL PIERCED | LE VOILE SE DÉCHIRE |
| THE GREAT SHADOW BREAKS APART | LA GRANDE OMBRE SE DISLOQUE |
| THE FOUNDRY LIES AHEAD | LA FONDERIE NOUS ATTEND |

### 6 — Sector 3 arrival

| English | French |
|---|---|
| IMPERIAL FOUNDRY | FONDERIE IMPÉRIALE |
| THEIR FURNACES NEVER SLEEP | LEURS FOURNEAUX NE DORMENT JAMAIS |
| WE WILL END THIS WAR MACHINE | BRISONS CETTE MACHINE DE GUERRE |

### 7 — Sector 3 boss

| English | French |
|---|---|
| FURNACE CARRIER | LE VAISSEAU FOURNAISE |
| THE FACTORY SHIP TURNS TO FIRE | LE VAISSEAU USINE SE PRÉPARE À TIRER |
| STAY CLEAR OF ITS GUN DECKS | ÉVITEZ SES BATTERIES |

### 8 — Sector 3 victory

| English | French |
|---|---|
| FURNACES SILENCED | LES FOURNEAUX SE TAISENT |
| NO MORE SHIPS FROM THESE FIRES | CES FEUX NE FORGERONT PLUS DE VAISSEAUX |
| ONE LAST JUMP TO THE CITADEL | UN DERNIER SAUT VERS LA CITADELLE |

### 9 — Sector 4 arrival

| English | French |
|---|---|
| STELLAR CITADEL | CITADELLE STELLAIRE |
| THE CROWN ECLIPSES OUR STAR | LA COURONNE ÉCLIPSE NOTRE ÉTOILE |
| THIS IS WHERE WE MAKE OUR STAND | C’EST ICI QUE NOUS RÉSISTERONS |

### 10 — Sector 4 boss

| English | French |
|---|---|
| REACTOR CROWN | LA COURONNE DU RÉACTEUR |
| ITS HALO IS GATHERING LIGHT | SON HALO ACCUMULE LA LUMIÈRE |
| BREAK THE CROWN BEFORE THE DAWN | BRISEZ LA COURONNE AVANT L’AUBE |

### 11 — Sector 4 victory

| English | French |
|---|---|
| THE CROWN FALLS | LA COURONNE TOMBE |
| THE REACTOR GOES DARK | LE RÉACTEUR S’ÉTEINT |
| LOOK BEYOND THE FALLING TOWERS | REGARDEZ AU-DELÀ DES TOURS EN RUINE |

### 12 — Ending

| English | French |
|---|---|
| DAWN RESTORED | L’AUBE RETROUVÉE |
| THE LAST LIGHT BURNS AGAIN | LA DERNIÈRE LUEUR BRILLE À NOUVEAU |
| WE MADE IT HOME | NOUS SOMMES RENTRÉS |

The current generator omits the ordinary entry headings (0/3/6/9) on narrative
cards. The ending displays its title and restart prompt rather than its authored
caption/reply. Those fields are translated here for completeness, not as a
proposal to change the current presentation.

## Integration and validation boundary

1. One bilingual catalog is shared by runtime strings and offline card
   generation. Select by the session preference without resetting it on death,
   return to title or replay. Do not duplicate shared narrative artwork.
2. Explicit glyph mapping covers French capitals and punctuation used above
   (À, Â, Ç, É, È, Ê, Î, apostrophe, hyphen and period). The existing A–Z/digit
   path cannot consume these UTF-8 strings safely; unsupported glyphs must cause
   a generation error, not disappear silently. The selector's bitmap cedilla
   alone does not provide general French support.
3. Narrative text reflows within the existing 28-character line constraint and
   vertical budget. Validate glyph widths, cached HUD labels, title layout and
   runtime byte-buffer limits independently of character counts.
4. Host tests check catalog completeness and both languages' generated rows; capture all
   13 scenes, title, HUD/charge states, pause, game over and ending on both native
   profiles. Measure added executable data, baseline A500 free memory and timing.
    Keep the existing 50fps acceptance gate unchanged.

### Encoding, ownership and bounded work

- Authoring is UTF-8 JSON. Generation rejects unsupported glyphs and emits
  uppercase CP1252 strings as ASCII C source with fixed three-digit octal escapes.
  A runtime byte is one glyph/cursor step, including accented capitals and `’`.
  Unsupported runtime bytes render a visible question mark; only spaces are blank.
- Accented 5×7 and 4×6 glyphs are authored in the catalog. Existing ASCII font
  pixels and their 6px/5px advances are preserved. Accents fit the existing heights.
- `game/tools/make-presentation.py` emits both `art/presentation-rows.h` and
  `art/localization.h`; `--check` checks both without writing. CMake tracks the
  catalog, font sources and localization helper. Story prose and small glyphs
  are baked offline rather than retained again as runtime strings.
- Cards/HUD select the `languageGet()` bank; five image streams remain shared.
  Decoder limits remain 320 output bytes / 64 operations per call. Runtime text
  remains at most two single-byte glyphs per composition step.
- One 96×56×4bpp startup label bitmap caches both languages, adding **1,344 CHIP
  bytes** over the former 96×28 bitmap. It is filled before hardware takeover;
  drawing selects the bank after language confirmation, without allocation.
  Eleven extra glyphs add **924 ordinary-memory mask bytes** (3 scales × 7 × 4).
- English coordinates are retained, including the historical GAMEOVER offsets.
  French GAMEOVER is centered at the same scale; the French title navigation
  row shifts left 6px to accommodate its two extra glyphs. The logo/subtitle
  retain their existing English text and layout.

### Validation record for this workspace

Baseline: 124 Python 3.12 tests passed before this integration. Generated
presentation payload baseline: **59,676 bytes**, including layouts and row tables.
New generated size and executed check results will be recorded after validation.

Ordinary English fixtures now explicitly choose the right-hand English flag
before confirming; their goldens are unchanged. New native fixtures (not yet run):

- `game/tests/native/localization_fr.agk`: all four titles, opening/HUD, ready,
  pause, release, ending, GAMEOVER and return-title persistence in production.
- `game/tests/native/localization_fr_campaign.agk`: all thirteen French scenes
  twice with the non-shipping campaign probe. Check captures using
  `python3.12 tools/verify-precomputed-cards.py --language fr <capture-directory>`.

Parent review owns final native checks on both `a500` and `a500-aros`, capture
inspection, fresh executable/free-CHIP measurements and worst-case timing. No
new native or full-game 50fps acceptance is claimed by the source integration.
