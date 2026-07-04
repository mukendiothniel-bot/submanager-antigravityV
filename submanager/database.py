import sqlite3
import datetime
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "submanager.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # Activer le support des clés étrangères pour que ON DELETE CASCADE fonctionne dans SQLite
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Table utilisateurs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS utilisateurs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nom TEXT NOT NULL,
        contact TEXT NOT NULL,
        statut TEXT DEFAULT 'Actif'
    );
    """)
    
    # 2. Table familles (places_max par défaut à 5)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS familles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nom_groupe TEXT NOT NULL,
        type_plateforme TEXT CHECK(type_plateforme IN ('Spotify', 'Apple')),
        places_max INTEGER DEFAULT 5
    );
    """)
    
    # 3. Table abonnements
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS abonnements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        famille_id INTEGER NOT NULL,
        date_debut TEXT NOT NULL, -- Format YYYY-MM-DD
        date_fin TEXT NOT NULL,   -- Format YYYY-MM-DD
        statut_paiement TEXT CHECK(statut_paiement IN ('Payé', 'En attente', 'Expiré')),
        FOREIGN KEY(user_id) REFERENCES utilisateurs(id) ON DELETE CASCADE,
        FOREIGN KEY(famille_id) REFERENCES familles(id) ON DELETE CASCADE
    );
    """)
    
    # Nettoyer les abonnements orphelins (au cas où des suppressions passées sans clés étrangères actives auraient laissé des traces)
    cursor.execute("""
    DELETE FROM abonnements 
    WHERE user_id NOT IN (SELECT id FROM utilisateurs) 
       OR famille_id NOT IN (SELECT id FROM familles);
    """)
    
    # Migration V1.1 : Mettre à jour les familles existantes de 6 places à 5 places
    cursor.execute("UPDATE familles SET places_max = 5 WHERE places_max = 6;")
    
    conn.commit()
    conn.close()


# --- CRUD Utilisateurs ---

def create_utilisateur(nom, contact, statut="Actif"):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO utilisateurs (nom, contact, statut) VALUES (?, ?, ?)",
        (nom, contact, statut)
    )
    conn.commit()
    user_id = cursor.lastrowid
    conn.close()
    return user_id

def get_utilisateurs():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM utilisateurs ORDER BY nom ASC")
    users = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return users

def get_utilisateur(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM utilisateurs WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def update_utilisateur(user_id, nom, contact, statut):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE utilisateurs SET nom = ?, contact = ?, statut = ? WHERE id = ?",
        (nom, contact, statut, user_id)
    )
    conn.commit()
    conn.close()

def delete_utilisateur(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM utilisateurs WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

# --- CRUD Familles ---

def create_famille(nom_groupe, type_plateforme, places_max=5):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO familles (nom_groupe, type_plateforme, places_max) VALUES (?, ?, ?)",
        (nom_groupe, type_plateforme, places_max)
    )
    conn.commit()
    famille_id = cursor.lastrowid
    conn.close()
    return famille_id


def get_familles():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Récupérer toutes les familles et calculer dynamiquement le nombre de places occupées
    # Une place est occupée si l'abonnement est actif (date_fin >= aujourd'hui et statut != 'Expiré')
    cursor.execute("SELECT * FROM familles ORDER BY nom_groupe ASC")
    familles = [dict(row) for row in cursor.fetchall()]
    
    today_str = datetime.date.today().isoformat()
    
    for f in familles:
        cursor.execute("""
            SELECT COUNT(*) as count FROM abonnements 
            WHERE famille_id = ? AND date_fin >= ? AND statut_paiement != 'Expiré'
        """, (f["id"], today_str))
        f["places_occupees"] = cursor.fetchone()["count"]
        f["places_libres"] = max(0, f["places_max"] - f["places_occupees"])
        
    conn.close()
    return familles

def get_famille(famille_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM familles WHERE id = ?", (famille_id,))
    row = cursor.fetchone()
    if row:
        f = dict(row)
        today_str = datetime.date.today().isoformat()
        cursor.execute("""
            SELECT COUNT(*) as count FROM abonnements 
            WHERE famille_id = ? AND date_fin >= ? AND statut_paiement != 'Expiré'
        """, (f["id"], today_str))
        f["places_occupees"] = cursor.fetchone()["count"]
        f["places_libres"] = max(0, f["places_max"] - f["places_occupees"])
    else:
        f = None
    conn.close()
    return f

def update_famille(famille_id, nom_groupe, type_plateforme, places_max):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE familles SET nom_groupe = ?, type_plateforme = ?, places_max = ? WHERE id = ?",
        (nom_groupe, type_plateforme, places_max, famille_id)
    )
    conn.commit()
    conn.close()

def delete_famille(famille_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM familles WHERE id = ?", (famille_id,))
    conn.commit()
    conn.close()

# --- CRUD Abonnements ---

def create_abonnement(user_id, famille_id, date_debut, date_fin, statut_paiement="Payé"):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO abonnements (user_id, famille_id, date_debut, date_fin, statut_paiement) VALUES (?, ?, ?, ?, ?)",
        (user_id, famille_id, date_debut, date_fin, statut_paiement)
    )
    conn.commit()
    sub_id = cursor.lastrowid
    conn.close()
    return sub_id

def get_abonnements():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.*, u.nom as user_nom, u.contact as user_contact, f.nom_groupe, f.type_plateforme
        FROM abonnements a
        JOIN utilisateurs u ON a.user_id = u.id
        JOIN familles f ON a.famille_id = f.id
        ORDER BY a.date_fin ASC
    """)
    abonnements = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return abonnements

def get_abonnement(sub_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.*, u.nom as user_nom, u.contact as user_contact, f.nom_groupe, f.type_plateforme
        FROM abonnements a
        JOIN utilisateurs u ON a.user_id = u.id
        JOIN familles f ON a.famille_id = f.id
        WHERE a.id = ?
    """, (sub_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def update_abonnement(sub_id, user_id, famille_id, date_debut, date_fin, statut_paiement):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE abonnements SET user_id = ?, famille_id = ?, date_debut = ?, date_fin = ?, statut_paiement = ? WHERE id = ?",
        (user_id, famille_id, date_debut, date_fin, statut_paiement, sub_id)
    )
    conn.commit()
    conn.close()

def delete_abonnement(sub_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM abonnements WHERE id = ?", (sub_id,))
    conn.commit()
    conn.close()
