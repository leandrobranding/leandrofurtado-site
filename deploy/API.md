# API de conteúdo

Canal para alimentar o site sem passar pelo painel. Serve para o Claude publicar cases,
posts e rascunhos de newsletter a partir do que o Leandro manda no chat.

## Token

Gere em **Admin → Configurações → API de conteúdo**. Ele começa com `lf_` e é a única
credencial que a API aceita. Sem token gerado a API responde `503`, com token errado `401`.

O token é separado da senha do admin de propósito: se vazar, você revoga só ele em
Configurações e a conta continua intacta. Nunca cole a senha do admin em lugar nenhum.

Todas as chamadas levam o cabeçalho:

```
Authorization: Bearer lf_seu_token_aqui
```

## Limite deliberado

A API **não dispara newsletter**. Ela cria a campanha como rascunho e devolve o link para
revisão. Mandar e-mail para pessoas reais é irreversível, então continua sendo um clique
seu no painel.

## Endpoints

Base: `https://leandrofurtado.com.br/api/v1`

### Diagnóstico

| Método | Rota | O que faz |
|---|---|---|
| `GET` | `/status` | Retrato do site: contagens, o que falta (cases sem capa, marcas sem logo) e quais integrações estão configuradas |

### Cases

| Método | Rota | O que faz |
|---|---|---|
| `GET` | `/cases` | Lista todos |
| `GET` | `/cases/{slug}` | Um case com corpo e mídias |
| `POST` | `/cases` | Cria ou atualiza (chave é o `slug`) |
| `POST` | `/cases/{slug}/capa` | Sobe a imagem de capa (multipart, campo `file`) |
| `POST` | `/cases/{slug}/midia` | Sobe uma mídia da galeria (multipart, campo `file`) |
| `DELETE` | `/cases/{slug}` | Remove o case e os arquivos dele |

Campos aceitos no `POST /cases`: `slug`, `titulo_pt`, `titulo_en`, `subtitulo_pt`,
`subtitulo_en`, `cliente`, `ano`, `funcao_pt`, `funcao_en`, `corpo_pt`, `corpo_en`
(Markdown), `categoria` (slug de uma categoria existente), `tags` (lista), `destaque`,
`publicado`.

Só mexe no que vier no corpo, então dá para mandar atualização parcial sem apagar o resto:

```bash
curl -X POST https://leandrofurtado.com.br/api/v1/cases \
  -H "Authorization: Bearer $LF_TOKEN" -H "Content-Type: application/json" \
  -d '{"slug": "meu-case", "ano": "2026"}'
```

**Publicar exige capa.** `{"publicado": true}` num case sem `cover_image` devolve `400`.
A ordem certa é: criar → subir capa → subir mídias → publicar.

### LinkedIn, perfil e newsletter

| Método | Rota | O que faz |
|---|---|---|
| `GET` `POST` | `/linkedin` | Lista / cria post (`resumo`, `tag`, `url`) |
| `DELETE` | `/linkedin/{id}` | Remove |
| `GET` | `/perfil` | Currículo completo em JSON |
| `PATCH` | `/perfil` | Mescla no primeiro nível: manda só a chave que mudou |
| `POST` | `/campanhas` | Cria newsletter como rascunho (`assunto`, `previa`, `corpo`, `botao_texto`, `botao_url`, `publico`) |

## Fluxo completo de um case

```bash
export LF_TOKEN=lf_seu_token
export LF=https://leandrofurtado.com.br/api/v1

# 1. cria
curl -X POST $LF/cases -H "Authorization: Bearer $LF_TOKEN" \
  -H "Content-Type: application/json" -d '{
    "titulo_pt": "Nome do case",
    "subtitulo_pt": "A frase que resume",
    "cliente": "Coca-Cola", "ano": "2026",
    "categoria": "branding", "tags": ["Key Visual", "IA"],
    "corpo_pt": "## O desafio\n\nTexto em Markdown."
  }'

# 2. capa
curl -X POST $LF/cases/nome-do-case/capa \
  -H "Authorization: Bearer $LF_TOKEN" -F "file=@capa.jpg"

# 3. mídias da galeria
curl -X POST $LF/cases/nome-do-case/midia \
  -H "Authorization: Bearer $LF_TOKEN" -F "file=@peca-01.jpg" -F "legenda_pt=Aplicação em OOH"

# 4. publica
curl -X POST $LF/cases -H "Authorization: Bearer $LF_TOKEN" \
  -H "Content-Type: application/json" -d '{"slug": "nome-do-case", "publicado": true}'
```
