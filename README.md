# Progetto Sistemi Distribuiti

*UNIVERSITÀ DEGLI STUDI DI URBINO CARLO BO*

Dipartimento di Scienze Pure e Applicate
Corso di Laurea in Informatica e Innovazione Digitale


## Sistema di Messaggistica Distribuita

             
Prof.             | Studente
---               | ---
Stefano Ferretti  | Nunzio D’Amore Mat. 329163





## Specifica del problema
Sviluppo di un sistema di messaggistica distribuita volto a garantire persistenza, disponibilità, auditing, integrità, confidenzialità ed efficienza nella consegna dei messaggi.

## Analisi del problema

### Struttura della rete
Per la realizzazione del sistema di messaggistica, è stata scelta una rete dedicata anziché soluzioni come IPFS o blockchain. Questa scelta offre maggiore flessibilità nella struttura della rete, permettendo di raggiungere meglio gli obiettivi prefissati.

Le entità in gioco nella rete sono tre:
- **Elite server**: sono server che hanno il compito di tenere traccia dell’intera rete permettendo l’inizializzazione dei nodi.
- **Server**: i server che provvedono al mantenimento di tutti i dati scambiati nella rete.
- **Client**: un qualsiasi dispositivo con cui gli utenti accedono al sistema per comunicare.

Questa suddivisione evidenzia diversi requisiti di memoria tra le entità, che sfrutteremo successivamente. Questa rete non si pone come obiettivo quello di garantire un utilizzo efficiente dell’archiviazione per ogni entità, ma preferisce garantire sicurezza, integrità e velocità.

La rete organizza i server in cluster utilizzando la funzione di hash SHA256 sugli indirizzi IP dei server, garantendone una distribuzione uniforme, soprattutto con un gran numero di server. Questa suddivisione permette di identificare rapidamente il gruppo di server responsabili della gestione di determinate informazioni.

Ogni cluster, infatti, rappresenta la casella di ricezione di ogni utente che questo individua effettuando l'hash del proprio username. Questo sistema permette di individuare facilmente i server a cui inoltrare un messaggio che si vuole consegnare ad un utente, effettuando l’hash dell’username del destinatario.

La scelta del numero di cluster presenti nella rete è molto importante, poiché regola la ridondanza in modo diretto (e conseguentemente la velocità di convergenza della rete / traffico). Questo perché il numero di server per cluster è inversamente proporzionale al numero di cluster stesso, e più server ci sono in un cluster più saranno le copie di ogni messaggio. Potrebbe quindi variare in base alla reale applicazione della rete e va scelto a tempo di progettazione.
 
La distribuzione spaziale disordinata dei server di un cluster è vantaggiosa, poiché consente di affidarsi ai server con minore latenza, indipendentemente dalla posizione geografica dell'utente. 
Inoltre, questa struttura garantisce l'efficienza nella consegna dei messaggi, poiché un utente attivo segnala ai server del proprio cluster il proprio indirizzo corrente, permettendo al messaggio di arrivare a destinazione in massimo due passaggi. La rete però prevede anche un sistema di gestione degli indirizzi dell’utente, qualora questo risultasse irraggiungibile (o per qualche motivo il server corrente non conosce l’indirizzo), affidando ad un altro server il dovere di inoltrare il messaggio.


## Sicurezza e integrità
Per garantire la sicurezza, confidenzialità e l’integrità delle comunicazioni, sono diversi gli algoritmi di cifratura utilizzati.

Ogni utente ha tre chiavi:
- **Chiave pubblica RSA (Rpub)**
- **Chiave privata RSA (Rpriv)**
- **Chiave pubblica ECDSA (E)**

Ogni utente firmerà i propri messaggi tramite l’algoritmo ECDSA che usa come chiave privata l’hash SHA256 della propria password (che ovviamente si presuppone essere sicura, ed eventualmente venga cambiata con una certa regolarità). A partire dalla password viene quindi generata una chiave pubblica (E) che permette a chiunque di verificare i messaggi dell’utente. 

Oltre al testo del messaggio l’utente firma anche l’ora di invio ed il destinatario, per prevenire alterazioni temporali o attacchi di replay. 
Per quanto riguarda la problematica temporale bisognerebbe per i messaggi più vecchi di una certa soglia verificare che più di N server riconoscano quell’informazione, per evitare che sia l’utente stesso a compromettere l’integrità temporale della conversazione.

Le chat sono criptate con chiavi AES, potenzialmente diverse per ogni messaggio. Ogni messaggio contiene anche la chiave AES criptata con la chiave Rpub di mittente e destinatario, permettendo solo agli interlocutori di decifrare il contenuto dei messaggi.

Le chiavi di firma e RSA in un caso d’uso reale – in cui bisogna gestire e garantire l’identità degli utenti - potrebbero essere generate e gestite da sistemi decentralizzati certificati (vedi Microsoft Decentralized Identity).


## Scoperta della rete
Ogni server/client che si collega alla rete avvierà un processo di discovery, collegandosi agli elite server. La risposta sarà creata in modo che ogni server conosca tutti i server del proprio cluster e solo una certa percentuale degli altri cluster. I client non hanno necessità di conoscere tutti i server della rete, si può quindi ridurre ad una certa percentuale anche i server del proprio cluster, riducendo al minimo lo spazio di archiviazione necessario.

Ogni server si presenta alla rete avviando una procedura di iscrizione, comunicando la sua disponibilità agli elite server, che informano tutti i server del cluster della presenza di un nuovo nodo. Il client comunica il suo indirizzo ai server del proprio cluster per una consegna immediata dei messaggi. 

Per evitare attacchi Sybil, si possono attuare diversi sistemi di protezione, partendo da un sistema reputazionale basato su feedback, per cui i server con reputazione migliore vengono scelti con più frequenza evitando o scartando del tutto i server con una cattiva reputazione. Inoltre, può essere utile integrare un sistema di identificazione anche degli utenti server con sistemi certificati.


## Comunicazione
Un utente a questo punto ha tutto ciò che serve per avviare una conversazione. Deciso il nome utente con cui comunicare, il client non dovrà fare altro che rilevare il server con minore latenza tra quelli conosciuti del cluster a cui l’hash del nome utente destinatario fa riferimento. 

Il server, ricevuto il messaggio, provvederà alla verifica della firma tramite la chiave pubblica del mittente per poi propagarlo a tutti gli altri server del cluster, scartando i duplicati.

I messaggi sono gestiti tramite una coda potendo dare precedenza ai messaggi più vecchi, che magari possono arrivare in ritardo, permettendo anche di evitare inutili aggiornamenti delle chat. La gestione dei messaggi tramite una coda permette anche di lasciare spazio per eventuali implementazioni di sistemi di gestione delle priorità.


## Consistenza
Alla ricezione di un messaggio propagato da altri server, il server ricevente provvede anche ad un controllo della versione attuale della chat, per poi eventualmente avviare una procedura di aggiornamento.

Anche i server che ricevono il messaggio propagato rispondono con la loro versione e hash della chat per permettere a chi propaga di accorgersi dell’esistenza di una nuova versione della chat.

La consistenza dei dati è garantita da un algoritmo che si divide in due step:
1. **Verifica del grafo sociale**: un server, soprattutto dopo essere appena entrato (o rientrato) nella rete, chiede la versione più aggiornata del grafo sociale del cluster per cercare nuove chat di cui non è ancora a conoscenza.
2. **Aggiornamento delle chat**: un server può decidere di aggiornare le chat sia nel momento della sua inizializzazione (anche dopo un periodo di inattività) o nel momento di ricezione di un messaggio, come descritto sopra. Questo processo richiede al server più aggiornato i messaggi mancanti tra coppie di messaggi, fino a convergenza.

Questo metodo permette di aggiornare le chat in modo efficiente, senza la necessità di scambiare l’intera conversazione, ma solo il necessario.

## Sistema di ricompense
In base alla specifica applicazione di questo modello, potrebbe essere anche utile un sistema di ricompense per incentivare la partecipazione di nuovi nodi alla rete.

Si può quindi pensare di introdurre una criptovaluta per la ricompensa di quegli utenti che mettono a disposizione il proprio spazio di archiviazione per la rete. Ovviamente nel caso del server si tratta di macchine con grandi capacità, essendo la rete molto ridondante. Questo comporta inevitabilmente una ricompensa più elevata.

Gli elite server sono server noti (almeno una parte di essi), che tengono traccia dell’intera rete. Per quanto oneroso dal punto di vista dell’archiviazione, molti dispositivi di uso personale moderni sono in grado – anche per una rete di grandi dimensioni – di gestirne il carico, il che comporta anche una ricompensa minore.

Poiché il client non contribuisce al mantenimento della rete, non sarebbe prevista alcuna ricompensa.

## Conclusioni
La rete così come descritta rispetta i vincoli prestabiliti:
- I messaggi se il client è attivo, impiegano due step per arrivare a destinazione, garantendo l’efficienza durante la consegna dei messaggi.
- La ridondanza è garantita dalla suddivisione in cluster di dimensione fissa, in modo che all’aumentare dei server nella rete aumentano anche il numero di copie presenti.
- L’integrità, la responsabilità e la confidenzialità sono garantite attraverso sistemi di cifratura e firma digitale con gli algoritmi ECSDA, RSA e AES. Il tutto dovrebbe poi essere migliorato, tramite sistemi di cambio delle chiavi pubbliche, della password e sistemi di autenticazione multifattore. Per applicazioni in cui è richiesto un maggiore livello di integrità si potrebbero gestire le chat (a livello unidirezionale) come delle mini-blockchain.
- La consistenza delle conversazioni è invece garantita attraverso un algoritmo di aggiornamento efficiente che analizza lo stato attuale e scambia solo i dati necessari riempiendo le lacune.

Il tutto va ovviamente a discapito dello spazio di archiviazione, richiedendo che i server abbiano grandi capacità. Questo limita la possibilità di partecipare alla rete come server, ma si può incentivare la partecipazione attraverso ricompense in criptovalute. Gli elite server, hanno bisogno di meno capacità, quindi anche in questo caso si può incentivare la partecipazione anche se con ricompense minori. In questo modo ogni utente può decidere di partecipare alla rete in base alle proprie disponibilità.

Gli utenti sono liberi di usare il dispositivo che più preferiscono per partecipare alla rete, conoscendo le credenziali di accesso.

Per di più si può garantire l’identità degli utenti appoggiandosi a sistemi di identificazione decentralizzati e certificati.

Questo tipo di sistemi possono essere usati per svariate applicazioni, in cui si richiede integrità, auditing, confidenzialità:
- scambio di dati sanitari o di ricerca e sviluppo
- settore finanziario
- settore governativo
- sistema di comunicazione e firma di contratti
- ecc

Ovviamente alcune di queste applicazioni necessitano di una attenta fase di regolamentazione, ma questa costituisce una buona base architetturale su cui appoggiare questo tipo di applicazioni.
