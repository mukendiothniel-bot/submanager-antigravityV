from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import database
import datetime
import urllib.parse
import os

app = FastAPI(title="SubManager", version="1.0")

# S'assurer que le dossier statique existe et que la base de données est initialisée
@app.on_event("startup")
def startup_event():
    database.init_db()

# --- Helpers ---

def clean_phone_number(phone: str) -> str:
    # Retire tout sauf les chiffres
    cleaned = "".join([c for c in phone if c.isdigit()])
    # Si le numéro commence par 0, c'est un numéro local français -> on ajoute l'indicatif 33
    if cleaned.startswith("0"):
        cleaned = "33" + cleaned[1:]
    return cleaned

# --- API Endpoints ---

@app.get("/api/dashboard")
def get_dashboard_data():
    try:
        users = database.get_utilisateurs()
        families = database.get_familles()
        subs = database.get_abonnements()
        
        today = datetime.date.today()
        today_str = today.isoformat()
        
        # 1. Calcul des statistiques
        total_clients = len(users)
        active_subs = 0
        pending_reminders = 0
        expired_subs = 0
        
        actions = []
        active_user_ids_with_sub = set()
        
        for s in subs:
            try:
                date_fin_parsed = datetime.date.fromisoformat(s["date_fin"])
            except ValueError:
                date_fin_parsed = today
                
            delta = (date_fin_parsed - today).days
            
            # Un abonnement est considéré comme actif s'il n'est pas expiré par statut et que la date de fin n'est pas dépassée
            if s["statut_paiement"] != "Expiré" and delta >= 0:
                active_subs += 1
                active_user_ids_with_sub.add(s["user_id"])
                
                # Relance nécessaire à J-2, J-1 ou J-0 (aujourd'hui)
                if delta in (0, 1, 2):
                    pending_reminders += 1
                    
                    # Génération du lien WhatsApp
                    raw_phone = s["user_contact"]
                    cleaned_phone = clean_phone_number(raw_phone)
                    plat = s["type_plateforme"]
                    fam_name = s["nom_groupe"]
                    
                    message = (
                        f"Bonjour {s['user_nom']},\n\n"
                        f"Votre abonnement de partage {plat} ({fam_name}) arrive à son terme le {s['date_fin']} (dans {delta} jours).\n"
                        f"Pourriez-vous effectuer le renouvellement pour conserver votre place ?\n\n"
                        f"Merci beaucoup !"
                    )
                    if delta == 0:
                        message = (
                            f"Bonjour {s['user_nom']},\n\n"
                            f"Votre abonnement de partage {plat} ({fam_name}) expire aujourd'hui ({s['date_fin']}).\n"
                            f"Pourriez-vous effectuer le renouvellement rapidement pour conserver votre place ?\n\n"
                            f"Merci beaucoup !"
                        )
                        
                    encoded_message = urllib.parse.quote(message)
                    wa_link = f"https://wa.me/{cleaned_phone}?text={encoded_message}"
                    
                    actions.append({
                        "id": f"relance_{s['id']}",
                        "sub_id": s["id"],
                        "type": "relance",
                        "client_nom": s["user_nom"],
                        "client_contact": s["user_contact"],
                        "famille_nom": s["nom_groupe"],
                        "famille_type": s["type_plateforme"],
                        "jours_restants": delta,
                        "date_fin": s["date_fin"],
                        "message": f"Relancer {s['user_nom']} - Expire dans {delta} jours ({s['date_fin']})",
                        "wa_link": wa_link
                    })
            else:
                expired_subs += 1
                
                # Si l'abonnement est dépassé mais pas encore marqué comme Expiré
                if s["statut_paiement"] != "Expiré" and delta < 0:
                    raw_phone = s["user_contact"]
                    cleaned_phone = clean_phone_number(raw_phone)
                    plat = s["type_plateforme"]
                    fam_name = s["nom_groupe"]
                    
                    message = (
                        f"Bonjour {s['user_nom']},\n\n"
                        f"Votre abonnement de partage {plat} ({fam_name}) est arrivé à échéance le {s['date_fin']} et a été suspendu.\n"
                        f"Pourriez-vous effectuer le renouvellement pour récupérer votre place ?\n\n"
                        f"Merci beaucoup !"
                    )
                    encoded_message = urllib.parse.quote(message)
                    wa_link = f"https://wa.me/{cleaned_phone}?text={encoded_message}"
                    
                    actions.append({
                        "id": f"retrait_{s['id']}",
                        "sub_id": s["id"],
                        "type": "retrait",
                        "client_nom": s["user_nom"],
                        "client_contact": s["user_contact"],
                        "famille_nom": s["nom_groupe"],
                        "famille_type": s["type_plateforme"],
                        "jours_depasses": -delta,
                        "date_fin": s["date_fin"],
                        "message": f"Retirer {s['user_nom']} de {s['nom_groupe']} ({s['type_plateforme']}) - Expiré depuis {-delta} jours",
                        "wa_link": wa_link
                    })
        
        # 2. Chercher les clients actifs sans abonnement en cours
        for u in users:
            if u["statut"] == "Actif" and u["id"] not in active_user_ids_with_sub:
                actions.append({
                    "id": f"affectation_{u['id']}",
                    "user_id": u["id"],
                    "type": "affectation",
                    "client_nom": u["nom"],
                    "client_contact": u["contact"],
                    "message": f"Attribuer une place à {u['nom']} (Client actif sans abonnement)"
                })
        
        # 3. Places libres par plateforme
        free_places_spotify = sum(f["places_libres"] for f in families if f["type_plateforme"] == "Spotify")
        free_places_apple = sum(f["places_libres"] for f in families if f["type_plateforme"] == "Apple")
        
        return {
            "stats": {
                "total_clients": total_clients,
                "active_subs": active_subs,
                "pending_reminders": pending_reminders,
                "expired_subs": expired_subs,
                "free_places_spotify": free_places_spotify,
                "free_places_apple": free_places_apple
            },
            "actions": actions,
            "familles": families
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- API CRUD Utilisateurs ---

@app.get("/api/users")
def get_users():
    return database.get_utilisateurs()

@app.post("/api/users")
async def create_user(request: Request):
    data = await request.json()
    nom = data.get("nom")
    contact = data.get("contact")
    statut = data.get("statut", "Actif")
    if not nom or not contact:
        raise HTTPException(status_code=400, detail="Nom et Contact requis")
    user_id = database.create_utilisateur(nom, contact, statut)
    return {"id": user_id, "nom": nom, "contact": contact, "statut": statut}

@app.put("/api/users/{user_id}")
async def update_user(user_id: int, request: Request):
    data = await request.json()
    nom = data.get("nom")
    contact = data.get("contact")
    statut = data.get("statut")
    if not nom or not contact or not statut:
        raise HTTPException(status_code=400, detail="Nom, Contact et Statut requis")
    database.update_utilisateur(user_id, nom, contact, statut)
    return {"status": "success"}

@app.delete("/api/users/{user_id}")
def delete_user(user_id: int):
    database.delete_utilisateur(user_id)
    return {"status": "success"}

# --- API CRUD Familles ---

@app.get("/api/families")
def get_families():
    return database.get_familles()

@app.post("/api/families")
async def create_family(request: Request):
    data = await request.json()
    nom_groupe = data.get("nom_groupe")
    type_plateforme = data.get("type_plateforme")
    places_max = int(data.get("places_max", 5))
    if not nom_groupe or not type_plateforme:
        raise HTTPException(status_code=400, detail="Nom du groupe et Type plateforme requis")
    fam_id = database.create_famille(nom_groupe, type_plateforme, places_max)
    return {"id": fam_id, "nom_groupe": nom_groupe, "type_plateforme": type_plateforme, "places_max": places_max}

@app.put("/api/families/{fam_id}")
async def update_family(fam_id: int, request: Request):
    data = await request.json()
    nom_groupe = data.get("nom_groupe")
    type_plateforme = data.get("type_plateforme")
    places_max = int(data.get("places_max", 5))
    if not nom_groupe or not type_plateforme:
        raise HTTPException(status_code=400, detail="Nom du groupe et Type plateforme requis")
    database.update_family(fam_id, nom_groupe, type_plateforme, places_max)
    return {"status": "success"}

@app.delete("/api/families/{fam_id}")
def delete_family(fam_id: int):
    database.delete_famille(fam_id)
    return {"status": "success"}


# --- API CRUD Abonnements ---

@app.get("/api/subscriptions")
def get_subscriptions():
    return database.get_abonnements()

@app.post("/api/subscriptions")
async def create_subscription(request: Request):
    data = await request.json()
    user_id = data.get("user_id")
    famille_id = data.get("famille_id")
    date_debut = data.get("date_debut")
    date_fin = data.get("date_fin")
    statut_paiement = data.get("statut_paiement", "Payé")
    
    if not user_id or not famille_id or not date_debut or not date_fin:
        raise HTTPException(status_code=400, detail="Tous les champs sont requis")
        
    # Vérifier s'il reste de la place dans la famille
    famille = database.get_famille(famille_id)
    if not famille:
        raise HTTPException(status_code=404, detail="Famille non trouvée")
    if famille["places_libres"] <= 0:
        raise HTTPException(status_code=400, detail="Cette famille est déjà complète")
        
    sub_id = database.create_abonnement(user_id, famille_id, date_debut, date_fin, statut_paiement)
    return {"id": sub_id, "status": "success"}

@app.put("/api/subscriptions/{sub_id}")
async def update_subscription(sub_id: int, request: Request):
    data = await request.json()
    user_id = data.get("user_id")
    famille_id = data.get("famille_id")
    date_debut = data.get("date_debut")
    date_fin = data.get("date_fin")
    statut_paiement = data.get("statut_paiement")
    
    if not user_id or not famille_id or not date_debut or not date_fin or not statut_paiement:
        raise HTTPException(status_code=400, detail="Tous les champs sont requis")
        
    database.update_abonnement(sub_id, user_id, famille_id, date_debut, date_fin, statut_paiement)
    return {"status": "success"}

@app.delete("/api/subscriptions/{sub_id}")
def delete_subscription(sub_id: int):
    database.delete_abonnement(sub_id)
    return {"status": "success"}

# Confirmer l'expiration/retrait d'un abonnement (met à jour le statut paiement à 'Expiré')
@app.post("/api/subscriptions/{sub_id}/expire")
def expire_subscription(sub_id: int):
    sub = database.get_abonnement(sub_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Abonnement non trouvé")
    
    # On met à jour le statut paiement à 'Expiré' et la date de fin à aujourd'hui
    today_str = datetime.date.today().isoformat()
    database.update_abonnement(
        sub_id=sub_id,
        user_id=sub["user_id"],
        famille_id=sub["famille_id"],
        date_debut=sub["date_debut"],
        date_fin=today_str,
        statut_paiement="Expiré"
    )
    return {"status": "success"}

# --- Servir l'Interface Frontend ---

# S'assurer que le dossier statique existe
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)

# Servir index.html à la racine
@app.get("/", response_class=HTMLResponse)
def read_root():
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>SubManager est prêt. static/index.html manquant.</h1>")

app.mount("/static", StaticFiles(directory=static_dir), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
