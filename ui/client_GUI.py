from datetime import datetime, timezone
import sys
import threading
import tkinter as tk

from model.client import Client
from model.message import Message

class ClientGUI:

    def __init__(self, my_address):
        self.my_address = my_address
        self.message_queue = []
        self.message_queue_lock = threading.Lock()
        self.create_login_frame()
        
        

    def login(self):
        username_input = self.entry_username.get()
        password_input = self.entry_password.get()


        try:
            self.client = Client(self.my_address,username_input, password_input)
            self.client.start_client(False)
            

            self.client.add_message_notification_listener(self.message_listener)

            self.login_window.destroy() 
            self.create_root_frame()
        except Exception as e:
            self.lbl_login_status.config(text="Credenziali errate. Riprova.", fg="red")

    def message_listener(self, message : Message):
        self.add_message(message.username, message.text, time=message.time[:16])

    def add_message(self, username, text, time = ""):
        self.chat_frame.config(state=tk.NORMAL)
        self.chat_frame.insert(tk.END, f"{username}: ", "bold")  
        self.chat_frame.insert(tk.END, f"{text}\n")
        self.chat_frame.insert(tk.END, f"{time}\n\n")
        self.chat_frame.tag_configure("bold", font=("Arial", 10, "bold"))
        self.chat_frame.config(state=tk.DISABLED)

    # Contenuto della finestra principale
    def send_message(self):
        message_text = self.entry_text.get("1.0", tk.END).strip()  
        
        if message_text and self.receiver:  
            result = self.client.send_message(self.receiver, message_text)
            if(result):
                self.add_message(self.client.username, message_text, str(datetime.now(timezone.utc))[:16])
                self.entry_text.delete("1.0", tk.END)      


    def set_up_chat(self):
        self.receiver = self.entry_recipient.get("1.0", tk.END).strip()
        self.client.update_chat(self.receiver)
        full_chat = self.client.get_full_chat(self.receiver)
        self.chat_frame.config(state=tk.NORMAL)
        self.chat_frame.delete("1.0", tk.END)
        self.chat_frame.config(state=tk.DISABLED)
        
        for message in full_chat:
            self.add_message(message.username, message.text,time=message.time[:16])

    def on_closing(self):
        self.root.destroy()
        self.client.close()
        sys.exit(0)



    def create_login_frame(self):
        # Finestra di accesso
        self.login_window = tk.Tk()
        self.login_window.title("Accesso")
        self.login_window.protocol("WM_DELETE_WINDOW", self.on_closing)
        # Etichetta dell'username
        lbl_username = tk.Label(self.login_window, text="Username:")
        lbl_username.grid(row=0, column=0, padx=5, pady=5)

        # Campo di inserimento dell'username
        self.entry_username = tk.Entry(self.login_window)
        self.entry_username.grid(row=0, column=1, padx=5, pady=5)

        # Etichetta della password
        lbl_password = tk.Label(self.login_window, text="Password:")
        lbl_password.grid(row=1, column=0, padx=5, pady=5)

        # Campo di inserimento della password
        self.entry_password = tk.Entry(self.login_window, show="*")
        self.entry_password.grid(row=1, column=1, padx=5, pady=5)

        # Pulsante di accesso
        btn_login = tk.Button(self.login_window, text="Accedi", command=self.login)
        btn_login.grid(row=2, columnspan=2, padx=5, pady=5)

        # Etichetta per lo stato del login
        self.lbl_login_status = tk.Label(self.login_window, text="")
        self.lbl_login_status.grid(row=3, columnspan=2, padx=5, pady=5)

        self.login_window.mainloop()

    def create_root_frame(self):
        # Finestra principale (nascosta finché non si effettua l'accesso)
        self.root = tk.Tk()
        self.root.title("DMS [" + str(self.my_address) + "]")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        # self.root.iconbitmap(default='icon.ico')  # Inserisci il percorso del tuo file icon.ico       


        self.chat_frame = tk.Text(self.root, height=20, width=50, state=tk.DISABLED)
        self.chat_frame.pack(pady=10)

        label_recipient = tk.Label(self.root, text="Destinatario", anchor="w", font=("Arial", 10, "bold"))
        label_recipient.pack()


        receiver_frame = tk.Frame(self.root)
        receiver_frame.pack()

        self.entry_recipient = tk.Text(receiver_frame, height=1, width=40)  
        self.entry_recipient.pack(pady=5, side=tk.LEFT)

        # Aggiungi un pulsante a destra di entry_recipient
        btn_ok = tk.Button(receiver_frame, text="OK", command=self.set_up_chat)
        btn_ok.pack(side=tk.RIGHT)       

        entry_text_frame = tk.Frame(self.root)
        entry_text_frame.pack()

        # Sposta il pulsante btn_send a destra di entry_text
        btn_send = tk.Button(entry_text_frame, text="Invia", command=self.send_message)
        btn_send.pack(side=tk.RIGHT)

        self.entry_text = tk.Text(entry_text_frame, height=3, width=40)
        self.entry_text.pack(pady=5,side=tk.LEFT)

        
        
        self.root.mainloop()