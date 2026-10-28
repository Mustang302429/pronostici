# Mettere online i pronostici (gratis, aggiornati da soli)

Una volta fatto, il sistema gira da solo sui server di GitHub 3 volte al giorno
(07:00, 13:00, 18:30) e pubblica la pagina web. Il tuo PC può restare spento.

## 1. Crea l'account
Vai su https://github.com e registrati (gratis).

## 2. Crea il repository
1. In alto a destra: "+" -> "New repository".
2. Repository name: `pronostici`
3. Scegli **Public** (le pagine web gratuite richiedono un repository pubblico).
4. NON spuntare nient'altro. Clicca "Create repository".

## 3. Carica i file
1. Nella pagina che si apre clicca il link **"uploading an existing file"**.
2. Apri la cartella `pronostici` sul PC, seleziona **tutto il suo contenuto**
   (Ctrl+A: cartelle `.github`, `motore`, `dati`, `docs` e gli altri file) e
   trascinalo nella pagina di GitHub. La cartella `.github` è importante.
3. Aspetta che finisca il caricamento e clicca **"Commit changes"**.

## 4. Attiva la pagina web
1. Nel repository: **Settings** -> menu a sinistra **Pages**.
2. Alla voce "Source" scegli **GitHub Actions**.

## 5. Primo avvio
1. Scheda **Actions** in alto. Se chiede conferma, clicca il pulsante verde
   per abilitare i workflow.
2. A sinistra clicca **"Aggiorna pronostici"** -> a destra **"Run workflow"** ->
   **"Run workflow"**.
3. Dopo 3-5 minuti compare una spunta verde.

## 6. Apri il sito
Indirizzo: `https://TUO-NOME-UTENTE.github.io/pronostici/`
(lo trovi anche in Settings -> Pages). Salvalo tra i preferiti del telefono.

Per aggiornare a mano in qualsiasi momento: Actions -> "Aggiorna pronostici" ->
"Run workflow".
