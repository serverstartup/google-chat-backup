# Revertir todo

El objetivo es dejar el proyecto como estaba antes de los backups. Son dos partes,
porque solo una tiene API.

> Orden recomendado: **1) haces los backups → 2) reversión manual → 3) `terraform destroy`.**

## 1. APIs — automático

```bash
cd terraform
terraform destroy
```

Con `disable_on_destroy = true` (por defecto), esto **deshabilita** `chat.googleapis.com`
y `people.googleapis.com` en el proyecto.

> ⚠️ **Si el proyecto es COMPARTIDO** (lo usan otros equipos o cargas), deshabilitar una
> API afecta a todo el proyecto, no solo a tu uso. Chat API y People API es muy improbable
> que las use otra carga, pero confírmalo antes de destruir.
>
> Si prefieres **no tocar las APIs** y revertir solo lo tuyo, pon `disable_on_destroy = false`
> en `terraform.tfvars`, y la reversión será únicamente la parte manual de abajo.

## 2. Lo que no tiene API — manual

En la consola de Google Cloud, proyecto correcto seleccionado:

- **Cliente OAuth de escritorio:** `APIs y servicios` → `Credenciales` → papelera sobre el
  cliente que creaste.
- **Pantalla de consentimiento:** quita los usuarios de prueba y los scopes, o deja la app
  en borrador. Si era Internal, puedes dejarla.
- **Config de la Chat app** (opcional): `Google Chat API` → Configuración, puedes vaciarla.

## 3. En local (cada persona)

Borra las credenciales y tokens que quedaron en disco:

```bash
rm -f scripts/client_secret_*.json scripts/token.json
```

Las carpetas de backup (`backup-*/`) consérvalas o muévelas a donde guardéis la copia final;
están en `.gitignore`, no se suben al repo.
