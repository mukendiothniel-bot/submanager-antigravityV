// --- State Management ---
let currentTab = 'dashboard';
let allClients = [];
let allFamilies = [];
let allSubscriptions = [];

// --- Page Initialization ---
document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    initDateDefaults();
    loadAllData();
});

// --- Navigation ---
function initNavigation() {
    const navItems = document.querySelectorAll('.nav-item');
    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const tabId = item.getAttribute('data-tab');
            switchTab(tabId);
        });
    });
}

function switchTab(tabId) {
    // Update active nav class
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
        if (item.getAttribute('data-tab') === tabId) {
            item.classList.add('active');
        }
    });

    // Update active content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    document.getElementById(`tab-${tabId}`).classList.add('active');

    // Update headers
    const titleMap = {
        'dashboard': { title: 'Actions du jour', subtitle: 'Automatisation du suivi des abonnements Spotify & Apple' },
        'clients': { title: 'Base Clients', subtitle: 'Gestion de vos clients et de leurs canaux de contact' },
        'families': { title: 'Familles de partage', subtitle: 'Répartition des comptes et des places disponibles' },
        'history': { title: 'Historique des abonnements', subtitle: 'Suivi temporel et financier complet' }
    };
    
    document.getElementById('tab-title').textContent = titleMap[tabId].title;
    document.getElementById('tab-subtitle').textContent = titleMap[tabId].subtitle;

    currentTab = tabId;
    loadTabContent(tabId);
}

// Set default dates in subscription form
function initDateDefaults() {
    const today = new Date();
    const formattedToday = today.toISOString().split('T')[0];
    
    // Default start date = today
    document.getElementById('sub-debut').value = formattedToday;
    
    // Default end date = today + 30 days
    const nextMonth = new Date(today);
    nextMonth.setDate(today.getDate() + 30);
    const formattedNextMonth = nextMonth.toISOString().split('T')[0];
    document.getElementById('sub-fin').value = formattedNextMonth;
}

// --- Data Fetching ---
function loadAllData() {
    loadTabContent(currentTab);
    // Prefetch collections for dropdowns
    fetchClients();
    fetchFamilies();
}

function loadTabContent(tabId) {
    if (tabId === 'dashboard') {
        loadDashboard();
    } else if (tabId === 'clients') {
        loadClients();
    } else if (tabId === 'families') {
        loadFamilies();
    } else if (tabId === 'history') {
        loadHistory();
    }
}

// --- Dashboard Logic ---
async function loadDashboard() {
    const actionsContainer = document.getElementById('actions-container');
    const familiesContainer = document.getElementById('families-container');
    
    try {
        const response = await fetch('/api/dashboard');
        const data = await response.json();
        
        // 1. Update stats
        document.getElementById('stat-total-clients').textContent = data.stats.total_clients;
        document.getElementById('stat-active-subs').textContent = data.stats.active_subs;
        document.getElementById('stat-pending-reminders').textContent = data.stats.pending_reminders;
        document.getElementById('stat-spotify-free').textContent = data.stats.free_places_spotify;
        document.getElementById('stat-apple-free').textContent = data.stats.free_places_apple;
        
        // 2. Actions Count badge
        document.getElementById('action-count').textContent = `${data.actions.length} action${data.actions.length > 1 ? 's' : ''}`;

        // 3. Render Actions
        actionsContainer.innerHTML = '';
        if (data.actions.length === 0) {
            actionsContainer.innerHTML = `
                <div class="empty-state">
                    <i class="fa-solid fa-circle-check" style="color: var(--success); font-size: 40px;"></i>
                    <h4>Aucune action requise</h4>
                    <p>Tous les abonnements sont en règle et toutes les places sont configurées.</p>
                </div>
            `;
        } else {
            data.actions.forEach(action => {
                let actionHtml = '';
                
                if (action.type === 'retrait') {
                    actionHtml = `
                        <div class="action-item retrait">
                            <div class="action-details">
                                <div class="action-badge">
                                    <i class="fa-solid fa-user-minus"></i>
                                </div>
                                <div class="action-text">
                                    <span class="action-title">${action.message}</span>
                                    <span class="action-desc">Contact : ${action.client_contact} | Date de fin : ${action.date_fin}</span>
                                </div>
                            </div>
                            <div class="action-buttons">
                                <button class="btn btn-secondary btn-whatsapp" onclick="openWhatsAppLink('${action.wa_link || ''}', '${action.client_contact}')" title="Relancer par courtoisie avant coupure">
                                    <i class="fa-brands fa-whatsapp"></i> Relancer
                                </button>
                                <button class="btn btn-primary" style="background-color: var(--danger);" onclick="confirmRetrait(${action.sub_id})">
                                    <i class="fa-solid fa-check"></i> Confirmer le retrait
                                </button>
                            </div>
                        </div>
                    `;
                } else if (action.type === 'relance') {
                    actionHtml = `
                        <div class="action-item relance">
                            <div class="action-details">
                                <div class="action-badge">
                                    <i class="fa-solid fa-bell"></i>
                                </div>
                                <div class="action-text">
                                    <span class="action-title">${action.message}</span>
                                    <span class="action-desc">Contact : ${action.client_contact} | Groupe : ${action.famille_nom}</span>
                                </div>
                            </div>
                            <div class="action-buttons">
                                <button class="btn btn-whatsapp btn" onclick="openWhatsAppLink('${action.wa_link}', '${action.client_contact}')">
                                    <i class="fa-brands fa-whatsapp"></i> Relancer WhatsApp
                                </button>
                            </div>
                        </div>
                    `;
                } else if (action.type === 'affectation') {
                    actionHtml = `
                        <div class="action-item affectation">
                            <div class="action-details">
                                <div class="action-badge">
                                    <i class="fa-solid fa-user-plus"></i>
                                </div>
                                <div class="action-text">
                                    <span class="action-title">${action.message}</span>
                                    <span class="action-desc">Contact : ${action.client_contact}</span>
                                </div>
                            </div>
                            <div class="action-buttons">
                                <button class="btn btn-primary" onclick="assignUserPlace(${action.user_id})">
                                    <i class="fa-solid fa-link"></i> Attribuer place
                                </button>
                            </div>
                        </div>
                    `;
                }
                
                actionsContainer.insertAdjacentHTML('beforeend', actionHtml);
            });
        }

        // 4. Render Families mini-overview
        familiesContainer.innerHTML = '';
        if (data.familles.length === 0) {
            familiesContainer.innerHTML = `
                <div class="empty-state">
                    <i class="fa-solid fa-users-slash"></i>
                    <p>Aucune famille configurée.</p>
                </div>
            `;
        } else {
            data.familles.forEach(f => {
                const percent = Math.min(100, Math.round((f.places_occupees / f.places_max) * 100));
                const platformClass = f.type_plateforme.toLowerCase();
                
                const famHtml = `
                    <div class="family-mini-card">
                        <div class="family-info-header">
                            <span class="family-name">${f.nom_groupe}</span>
                            <span class="family-platform-badge ${platformClass}">${f.type_plateforme}</span>
                        </div>
                        <div class="family-progress-container">
                            <div class="progress-bar-bg">
                                <div class="progress-bar-fill ${platformClass}" style="width: ${percent}%;"></div>
                            </div>
                            <span class="places-count">${f.places_occupees}/${f.places_max}</span>
                        </div>
                    </div>
                `;
                familiesContainer.insertAdjacentHTML('beforeend', famHtml);
            });
        }

    } catch (error) {
        console.error('Error loading dashboard:', error);
        actionsContainer.innerHTML = `<div class="empty-state text-danger"><p>Erreur lors du chargement des données.</p></div>`;
    }
}

// --- WhatsApp Dispatcher ---
function openWhatsAppLink(link, contact) {
    if (link) {
        window.open(link, '_blank');
    } else {
        // Nettoyer le numéro de téléphone pour le lien wa.me (chiffres uniquement)
        let cleanedContact = contact.replace(/\D/g, '');
        if (cleanedContact.startsWith('0')) {
            cleanedContact = '33' + cleanedContact.substring(1);
        }
        const text = encodeURIComponent("Bonjour, votre abonnement est arrivé à échéance. Merci de procéder au renouvellement.");
        window.open(`https://wa.me/${cleanedContact}?text=${text}`, '_blank');
    }
}

// --- Confirm Action: Expirer abonnement ---
async function confirmRetrait(subId) {
    if (confirm("Confirmez-vous le retrait de ce membre du groupe familial (effectué manuellement sur votre appareil) ?")) {
        try {
            const res = await fetch(`/api/subscriptions/${subId}/expire`, { method: 'POST' });
            if (res.ok) {
                loadDashboard();
            } else {
                alert("Erreur lors de la validation du retrait.");
            }
        } catch (e) {
            console.error(e);
        }
    }
}

// --- Pre-fill Assignment Form ---
function assignUserPlace(userId) {
    openModal('modal-add-subscription');
    document.getElementById('sub-client').value = userId;
}

// --- Clients Management ---
async function fetchClients() {
    try {
        const res = await fetch('/api/users');
        allClients = await res.json();
        populateClientsDropdown();
    } catch (e) {
        console.error("Error fetching clients:", e);
    }
}

function populateClientsDropdown() {
    const subClientSelect = document.getElementById('sub-client');
    // Save current selected value
    const currentVal = subClientSelect.value;
    
    subClientSelect.innerHTML = '<option value="" disabled selected>Choisir un client...</option>';
    allClients.forEach(c => {
        if (c.statut === 'Actif') {
            const opt = document.createElement('option');
            opt.value = c.id;
            opt.textContent = `${c.nom} (${c.contact})`;
            subClientSelect.appendChild(opt);
        }
    });
    
    if (currentVal) {
        subClientSelect.value = currentVal;
    }
}

async function loadClients() {
    const tbody = document.getElementById('clients-table-body');
    tbody.innerHTML = '<tr><td colspan="4" class="loading-state"><i class="fa-solid fa-circle-notch fa-spin"></i></td></tr>';
    
    await fetchClients();
    renderClientsTable(allClients);
}

function renderClientsTable(users) {
    const tbody = document.getElementById('clients-table-body');
    tbody.innerHTML = '';
    
    if (users.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align: center; padding: 24px; color: var(--text-muted);">Aucun client trouvé.</td></tr>';
        return;
    }
    
    users.forEach(u => {
        const badgeClass = u.statut === 'Actif' ? 'badge-success' : 'badge-danger';
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><strong>${u.nom}</strong></td>
            <td>${u.contact}</td>
            <td><span class="badge ${badgeClass}">${u.statut}</span></td>
            <td>
                <button class="btn btn-secondary btn-icon" onclick="deleteClient(${u.id})" title="Supprimer"><i class="fa-solid fa-trash text-danger"></i></button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

// Client search filter
document.getElementById('client-search')?.addEventListener('input', (e) => {
    const search = e.target.value.toLowerCase().trim();
    if (!search) {
        renderClientsTable(allClients);
        return;
    }
    const filtered = allClients.filter(c => 
        c.nom.toLowerCase().includes(search) || 
        c.contact.toLowerCase().includes(search)
    );
    renderClientsTable(filtered);
});

// --- Families Management ---
async function fetchFamilies() {
    try {
        const res = await fetch('/api/families');
        allFamilies = await res.json();
        populateFamiliesDropdown();
    } catch (e) {
        console.error("Error fetching families:", e);
    }
}

function populateFamiliesDropdown() {
    const subFamilySelect = document.getElementById('sub-family');
    const currentVal = subFamilySelect.value;
    
    subFamilySelect.innerHTML = '<option value="" disabled selected>Choisir une famille...</option>';
    allFamilies.forEach(f => {
        if (f.places_libres > 0) {
            const opt = document.createElement('option');
            opt.value = f.id;
            opt.textContent = `${f.nom_groupe} (${f.type_plateforme}) - ${f.places_libres} places libres`;
            subFamilySelect.appendChild(opt);
        }
    });
    
    if (currentVal) {
        subFamilySelect.value = currentVal;
    }
}

async function loadFamilies() {
    const tbody = document.getElementById('families-table-body');
    tbody.innerHTML = '<tr><td colspan="6" class="loading-state"><i class="fa-solid fa-circle-notch fa-spin"></i></td></tr>';
    
    await fetchFamilies();
    tbody.innerHTML = '';
    
    if (allFamilies.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; padding: 24px; color: var(--text-muted);">Aucune famille configurée.</td></tr>';
        return;
    }
    
    allFamilies.forEach(f => {
        const platBadge = f.type_plateforme.toLowerCase() === 'spotify' ? 'spotify' : 'apple';
        const isFull = f.places_libres === 0;
        const statusBadge = isFull ? 'badge-danger' : 'badge-success';
        const statusText = isFull ? 'Complet' : 'Places libres';
        
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><strong>${f.nom_groupe}</strong></td>
            <td><span class="family-platform-badge ${platBadge}">${f.type_plateforme}</span></td>
            <td>${f.places_occupees}</td>
            <td>${f.places_max}</td>
            <td><span class="badge ${statusBadge}">${statusText}</span></td>
            <td>
                <button class="btn btn-secondary btn-icon" onclick="deleteFamily(${f.id})" title="Supprimer"><i class="fa-solid fa-trash text-danger"></i></button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

// --- History / Subscriptions Management ---
async function loadHistory() {
    const tbody = document.getElementById('subscriptions-table-body');
    tbody.innerHTML = '<tr><td colspan="7" class="loading-state"><i class="fa-solid fa-circle-notch fa-spin"></i></td></tr>';
    
    try {
        const res = await fetch('/api/subscriptions');
        allSubscriptions = await res.json();
        
        tbody.innerHTML = '';
        if (allSubscriptions.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; padding: 24px; color: var(--text-muted);">Aucun historique d\'abonnement enregistré.</td></tr>';
            return;
        }
        
        allSubscriptions.forEach(s => {
            const today = new Date().toISOString().split('T')[0];
            let badgeClass = 'badge-success';
            
            if (s.statut_paiement === 'Expiré' || s.date_fin < today) {
                badgeClass = 'badge-danger';
            } else if (s.statut_paiement === 'En attente') {
                badgeClass = 'badge-warning';
            }
            
            const platBadge = s.type_plateforme.toLowerCase() === 'spotify' ? 'spotify' : 'apple';
            
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><strong>${s.user_nom}</strong></td>
                <td>${s.nom_groupe}</td>
                <td><span class="family-platform-badge ${platBadge}">${s.type_plateforme}</span></td>
                <td>${s.date_debut}</td>
                <td>${s.date_fin}</td>
                <td><span class="badge ${badgeClass}">${s.statut_paiement === 'Expiré' || s.date_fin < today ? 'Expiré' : s.statut_paiement}</span></td>
                <td>
                    <button class="btn btn-secondary btn-icon" onclick="deleteSubscription(${s.id})" title="Supprimer de l'historique"><i class="fa-solid fa-trash text-danger"></i></button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (e) {
        console.error("Error loading subscriptions:", e);
        tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--danger);">Erreur de chargement.</td></tr>';
    }
}

// --- Actions : Deletes ---
async function deleteClient(id) {
    if (confirm("Voulez-vous vraiment supprimer ce client ? Tous ses abonnements associés seront également supprimés.")) {
        await fetch(`/api/users/${id}`, { method: 'DELETE' });
        loadClients();
        fetchClients();
    }
}

async function deleteFamily(id) {
    if (confirm("Voulez-vous vraiment supprimer cette famille ?")) {
        await fetch(`/api/families/${id}`, { method: 'DELETE' });
        loadFamilies();
        fetchFamilies();
    }
}

async function deleteSubscription(id) {
    if (confirm("Voulez-vous supprimer cet enregistrement d'abonnement ?")) {
        await fetch(`/api/subscriptions/${id}`, { method: 'DELETE' });
        loadHistory();
    }
}

// --- Forms Submissions ---

async function submitAddClient(event) {
    event.preventDefault();
    const nom = document.getElementById('client-nom').value;
    const contact = document.getElementById('client-contact').value;
    const statut = document.getElementById('client-statut').value;
    
    try {
        const res = await fetch('/api/users', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ nom, contact, statut })
        });
        
        if (res.ok) {
            closeModal('modal-add-client');
            document.getElementById('form-add-client').reset();
            loadAllData();
        } else {
            const err = await res.json();
            alert(`Erreur : ${err.detail}`);
        }
    } catch (e) {
        console.error(e);
    }
}

async function submitAddFamily(event) {
    event.preventDefault();
    const nom_groupe = document.getElementById('family-nom').value;
    const type_plateforme = document.getElementById('family-type').value;
    const places_max = document.getElementById('family-places').value;
    
    try {
        const res = await fetch('/api/families', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ nom_groupe, type_plateforme, places_max })
        });
        
        if (res.ok) {
            closeModal('modal-add-family');
            document.getElementById('form-add-family').reset();
            loadAllData();
        } else {
            const err = await res.json();
            alert(`Erreur : ${err.detail}`);
        }
    } catch (e) {
        console.error(e);
    }
}

async function submitAddSubscription(event) {
    event.preventDefault();
    const user_id = document.getElementById('sub-client').value;
    const famille_id = document.getElementById('sub-family').value;
    const date_debut = document.getElementById('sub-debut').value;
    const date_fin = document.getElementById('sub-fin').value;
    const statut_paiement = document.getElementById('sub-paiement').value;
    
    try {
        const res = await fetch('/api/subscriptions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id, famille_id, date_debut, date_fin, statut_paiement })
        });
        
        if (res.ok) {
            closeModal('modal-add-subscription');
            document.getElementById('form-add-subscription').reset();
            initDateDefaults();
            loadAllData();
        } else {
            const err = await res.json();
            alert(`Erreur : ${err.detail}`);
        }
    } catch (e) {
        console.error(e);
    }
}

// --- Modal Helper Functions ---
window.openModal = function(modalId) {
    document.getElementById(modalId).classList.add('open');
};

window.closeModal = function(modalId) {
    document.getElementById(modalId).classList.remove('open');
};

// Close modal when clicking outside content
window.onclick = function(event) {
    if (event.target.classList.contains('modal')) {
        event.target.classList.remove('open');
    }
};
