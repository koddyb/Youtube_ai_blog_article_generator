# **Déployer une application en production sur un VPS : Guide complet et simplifié**

Vous hésitez à utiliser un **VPS** pour déployer vos applications en production ? Vous craignez la complexité de la configuration ? Découvrez dans ce guide comment transformer un VPS en un environnement **production-ready** en moins de temps qu’il n’en faut pour le dire !

Dans cet article, nous explorons :
✅ **Pourquoi choisir un VPS plutôt qu’un serveurless ?**
✅ **Les étapes clés pour configurer un VPS sécurisé et performant**
✅ **Les outils indispensables (Traefik, Docker, Watchtower, etc.)**
✅ **Un exemple concret avec un déploiement automatisé**

---

## **Pourquoi opter pour un VPS plutôt qu’un serveurless ?**

Les plateformes **serverless** (comme AWS Lambda, Vercel ou Netlify) sont pratiques pour des tâches ponctuelles, mais elles présentent des limites :
⚠ **Coûts imprévisibles** : Les tâches longues ou les transferts massifs de données peuvent générer des factures exorbitantes.
⚠ **Complexité pour les tâches persistantes** : Les fonctions serverless ne sont pas optimisées pour les applications en continu.

À l’inverse, un **VPS (Virtual Private Server)** offre :
✔ **Une facturation prévisible** (ex. : **6,99 $/mois** chez Hostinger avec 8 Go de RAM et 100 Go de stockage).
✔ **Un contrôle total** sur l’infrastructure.
✔ **Une meilleure performance** pour les applications gourmandes.

> 💡 **Exemple** : Transférer 8 To de données sur un serveurless peut coûter **plus de 1 000 $**, contre **6,99 $** sur un VPS Hostinger.

---

## **Les 8 exigences pour un VPS "production-ready"**

Avant de déployer, définissons ce qu’un environnement **production-ready** doit inclure :

1. **Un nom de domaine pointé vers le serveur** (ex. : `monapp.com`).
2. **Une application fonctionnelle** (ex. : une application web en Go).
3. **Des bonnes pratiques de sécurité** :
   - Chiffrement TLS (HTTPS).
   - Renouvellement automatique des certificats.
   - Durcissement SSH (désactivation de l’authentification par mot de passe).
   - Pare-feu configuré (UFW).
4. **Une haute disponibilité** (même sur un seul nœud) :
   - Load balancing (répartition de charge).
5. **Une expérience développeur optimisée** :
   - Déploiements automatisés (CI/CD simplifié).
6. **Une surveillance proactive** :
   - Alertes en cas de panne (Uptime Robot).
7. **Un reverse proxy** (Traefik) pour gérer le trafic HTTP/HTTPS.
8. **Une base de données sécurisée** (PostgreSQL).

---

## **Étape 1 : Configurer le VPS avec Hostinger**

### **🔹 Choix du VPS et installation du système**
Hostinger propose des VPS **KVM** à partir de **6,99 $/mois** (avec 2 vCPUs et 8 Go de RAM). Voici comment le configurer :

1. **Sélectionnez un OS** :
   - Choisissez **Ubuntu 24.04 LTS** (recommandé pour sa stabilité).
   - Désactivez **Monarx** (scanner de sécurité inutile pour notre cas).

2. **Sécurisez l’accès SSH** :
   - Définissez un **mot de passe root fort**.
   - Ajoutez votre **clé SSH publique** pour éviter les connexions par mot de passe.

3. **Déployez le VPS** et connectez-vous en SSH :
   ```bash
   ssh root@<IP_DU_VPS>
   ```

---

## **Étape 2 : Sécuriser le serveur**

### **🔹 Créer un utilisateur non-root et configurer sudo**
```bash
adduser elliot  # Remplacez "elliot" par votre nom d'utilisateur
usermod -aG sudo elliot  # Ajoutez l'utilisateur au groupe sudo
su - elliot  # Passez à l'utilisateur créé
```

### **🔹 Désactiver l’authentification par mot de passe SSH**
1. Copiez votre clé SSH vers le nouvel utilisateur :
   ```bash
   ssh-copy-id elliot@<IP_DU_VPS>
   ```
2. Modifiez la configuration SSH :
   ```bash
   sudo vim /etc/ssh/sshd_config
   ```
   - Changez `PasswordAuthentication yes` → `no`
   - Désactivez `PermitRootLogin yes` → `no`
   - Sauvegardez (`:wq`) et rechargez SSH :
     ```bash
     sudo systemctl restart sshd
     ```

> ⚠ **Important** : Testez la connexion SSH **avant** de fermer votre session actuelle !

---

## **Étape 3 : Configurer le DNS et le pare-feu**

### **🔹 Pointer un nom de domaine vers le VPS**
1. Achetez un domaine (ex. : chez Hostinger pour **1,99 $/an**).
2. Dans le panneau Hostinger, ajoutez un **enregistrement A** pointant vers l’IP du VPS :
   ```
   Type : A
   Nom : @
   Valeur : <IP_DU_VPS>
   TTL : 3600
   ```
3. Vérifiez la propagation avec :
   ```bash
   nslookup monapp.com
   ```

### **🔹 Configurer le pare-feu (UFW)**
```bash
sudo ufw default deny incoming  # Bloque tout le trafic entrant par défaut
sudo ufw default allow outgoing  # Autorise tout le trafic sortant
sudo ufw allow 22/tcp           # Autorise SSH
sudo ufw enable                 # Active le pare-feu
```

> ⚠ **Attention** : Si vous oubliez d’autoriser SSH, vous perdrez l’accès au serveur !

---

## **Étape 4 : Déployer l’application avec Docker & Traefik**

### **🔹 Installer Docker et Docker Compose**
```bash
sudo apt update
sudo apt install -y docker.io docker-compose-plugin
sudo usermod -aG docker elliot  # Permet à l'utilisateur d'utiliser Docker sans sudo
```

### **🔹 Configurer Traefik (reverse proxy + TLS automatique)**
Traefik est un **reverse proxy moderne** qui gère :
- Le **load balancing**.
- Les **certificats TLS gratuits** (Let’s Encrypt).
- Le **routage dynamique**.

1. Créez un fichier `docker-compose.yml` :
   ```yaml
   version: '3.8'

   services:
     reverse-proxy:
       image: traefik:v3.1
       command:
         - "--providers.docker=true"
         - "--entrypoints.web.address=:80"
         - "--entrypoints.websecure.address=:443"
         - "--certificatesresolvers.myresolver.acme.tlschallenge=true"
         - "--certificatesresolvers.myresolver.acme.email=votre@email.com"
         - "--certificatesresolvers.myresolver.acme.storage=/letsencrypt/acme.json"
       ports:
         - "80:80"
         - "443:443"
         - "8080:8080"  # Dashboard Traefik
       volumes:
         - "/var/run/docker.sock:/var/run/docker.sock:ro"
         - "./letsencrypt:/letsencrypt"

     guestbook:
       image: ghcr.io/votre-utilisateur/guestbook:prod
       labels:
         - "traefik.enable=true"
         - "traefik.http.routers.guestbook.rule=Host(`monapp.com`)"
         - "traefik.http.routers.guestbook.entrypoints=websecure"
         - "traefik.http.routers.guestbook.tls.certresolver=myresolver"
   ```

2. Lancez les services :
   ```bash
   docker compose up -d
   ```

3. Accédez au **dashboard Traefik** :
   - `https://monapp.com:8080`

---

## **Étape 5 : Automatiser les déploiements avec Watchtower**

Watchtower **surveille les mises à jour des conteneurs Docker** et les redéploie automatiquement.

1. Ajoutez Watchtower au `docker-compose.yml` :
   ```yaml
   watchtower:
     image: containrrr/watchtower
     command: --label-enable --interval 30
     volumes:
       - "/var/run/docker.sock:/var/run/docker.sock"
   ```

2. Ajoutez un label à votre service `guestbook` :
   ```yaml
   labels:
     - "com.centurylinklabs.watchtower.enable=true"
   ```

3. Redémarrez Docker Compose :
   ```bash
   docker compose up -d
   ```

> ✅ **Résultat** : Toute nouvelle version de votre image Docker sera déployée **automatiquement** !

---

## **Étape 6 : Surveiller la disponibilité avec Uptime Robot**

Pour être alerté en cas de panne, utilisez **Uptime Robot** (gratuit) :
1. Inscrivez-vous sur [uptimerobot.com](https://uptimerobot.com/).
2. Ajoutez une **monitoring** pour `https://monapp.com`.
3. Configurez une **notification par email** en cas de downtime.

---

## **Conclusion : Votre VPS est prêt pour la production !**

En suivant ces étapes, vous avez transformé un **VPS basique** en un environnement **sécurisé, scalable et automatisé** :

✅ **Sécurité renforcée** (SSH, pare-feu, TLS).
✅ **Déploiements automatisés** (Watchtower).
✅ **Load balancing et haute disponibilité** (Traefik).
✅ **Surveillance proactive** (Uptime Robot).

> 🚀 **Prochaine étape** : Automatisez tout avec **GitHub Actions** pour un pipeline CI/CD complet !

---

### **🎁 Offre spéciale Hostinger**
Si vous souhaitez tester un VPS, **Hostinger** propose :
- **6,99 $/mois** pour un VPS KVM 2 (2 vCPUs, 8 Go RAM).
- **100 Go de stockage SSD**.
- **8 To de bande passante/mois**.

👉 **Utilisez le code promo `DREAMSOFCODE` pour obtenir une réduction supplémentaire !**

🔗 [Voir les offres Hostinger](https://www.hostinger.com/)

---
**💬 Partagez votre expérience en commentaire !** Avez-vous déjà déployé une application sur un VPS ? Quels outils utilisez-vous ?