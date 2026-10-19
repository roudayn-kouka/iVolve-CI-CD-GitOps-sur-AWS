# ☸️ Manifestes Kubernetes

Ressources déployées par ArgoCD dans le namespace `ivolve`, assemblées par **Kustomize**.

| Fichier | Rôle |
|---|---|
| `namespace.yaml` | Namespace avec Pod Security Admission **`restricted`** |
| `deployment.yaml` | 2 réplicas, rolling update `maxUnavailable: 0`, sondes, `resources`, `securityContext` durci, répartition par nœud |
| `service.yaml` | `NodePort` fixe **30080** → port 5000 des pods |
| `hpa.yaml` | HorizontalPodAutoscaler 2 → 5 pods à 70 % de CPU (nécessite metrics-server, installé par Ansible) |
| `pdb.yaml` | PodDisruptionBudget `minAvailable: 1` |
| `kustomization.yaml` | Assemble les ressources et porte **`images:`** (`newName` / `newTag`) |

## Comment le tag d'image est mis à jour

Le `Deployment` référence `image: ivolve-webapp` (un simple nom). C'est `kustomization.yaml` qui le remplace :

```yaml
images:
  - name: ivolve-webapp
    newName: docker.io/<utilisateur>/ivolve-webapp
    newTag: "128-a1b2c3d4"       # ← réécrit par le stage « Mise à jour GitOps » du Jenkinsfile
```

Un `git log` sur ce fichier donne donc **l'historique exact des déploiements**.

## Valider en local

```bash
kustomize build k8s-manifests | kubeconform -strict -summary
kustomize build k8s-manifests | kubectl apply --dry-run=client -f -
```

## Pourquoi pas d'Ingress ?

`ingress-nginx` a été archivé en mars 2026 (plus de correctifs de sécurité). Le NodePort suffit pour ce projet ; pour la suite, voir la Gateway API dans les pistes d'évolution du README principal.
