# Guia: conectar o KPI Hitachi ao Google Drive

Este guia mostra como criar as credenciais do Google para que o portal salve
automaticamente holerite e cartão ponto na sua pasta do Drive, assim que o
status do documento ficar **OK**.

## Como funciona

Quando o holerite ou o cartão ponto de um colaborador fica **OK** (assinado),
o portal:

1. Cria (ou reaproveita, se já existir) uma pasta com o nome da competência
   dentro da sua pasta raiz do Drive — exemplo: `07/2026`.
2. Dentro dela, cria (ou reaproveita) uma subpasta `Holerite` ou `Cartão Ponto`.
3. Salva o PDF lá com o nome `NOME DO COLABORADOR - TIPO DE DOCUMENTO.pdf`
   — exemplo: `ALESSANDRA DA SILVA ASSEN - CARTAO PONTO.pdf`.

Sua pasta raiz já está configurada por padrão como a pasta do link que você
passou (`https://drive.google.com/drive/folders/1LyjXgkF9p9TrWH39TbKly0oCG7HXNfRc`).

Isso roda direto no navegador (não existe um servidor do portal enviando os
arquivos) — por isso é necessário autorizar o portal a acessar o seu Google
Drive, com o fluxo de login do Google. Essa autorização vale por sessão do
navegador; expira depois de um tempo e pode pedir para conectar de novo.

## Passo 1 — Descubra a URL do seu portal no Streamlit

Abra o portal no navegador (a tela que você já usa hoje) e copie a URL que
aparece, só até o domínio — sem nada depois da barra. Normalmente é algo como:

```
https://SEU-APP.streamlit.app
```

Você vai precisar exatamente dessa URL no Passo 4.

## Passo 2 — Crie um projeto no Google Cloud

1. Acesse https://console.cloud.google.com/
2. Entre com a conta Google que vai administrar essa integração (pode ser a
   mesma conta dona da pasta do Drive, ou uma conta de serviço da empresa).
3. No topo, clique no seletor de projeto e depois em **Novo projeto**.
4. Dê um nome, por exemplo `Portal MSE - KPI Hitachi`, e clique em **Criar**.
5. Espere a notificação de que o projeto foi criado e selecione-o.

## Passo 3 — Ative a API do Google Drive

1. No menu lateral, vá em **APIs e serviços > Biblioteca**.
2. Busque por `Google Drive API`.
3. Abra o resultado e clique em **Ativar**.

## Passo 4 — Configure a Tela de consentimento OAuth

1. No menu lateral, vá em **APIs e serviços > Tela de consentimento OAuth**.
2. Tipo de usuário: escolha **Externo** (a menos que sua empresa use Google
   Workspace com um domínio próprio — nesse caso pode escolher **Interno**,
   o que evita a etapa de usuários de teste abaixo).
3. Preencha nome do app (`Portal MSE`), e-mail de suporte e e-mail do
   desenvolvedor com o seu e-mail.
4. Em **Escopos**, não precisa adicionar nada aqui agora — o portal já pede o
   escopo certo (`https://www.googleapis.com/auth/drive`) na hora do login.
5. Se o tipo for **Externo**, na etapa **Usuários de teste**, adicione o
   e-mail Google de cada pessoa que vai usar o botão "Conectar Google Drive"
   no portal (inclusive o seu). Enquanto o app estiver em modo de teste, só
   esses e-mails conseguem autorizar.
6. Salve e conclua.

> O escopo `drive` (acesso completo ao Drive) é classificado pelo Google como
> "sensível". Para uso interno, com o app em modo de teste e você mesma como
> usuária de teste, isso funciona sem passar por revisão do Google. Se um dia
> quiser liberar esse login para muita gente fora da empresa, o Google pode
> pedir uma verificação do app — não é o caso aqui.

## Passo 5 — Crie o Client ID OAuth

1. No menu lateral, vá em **APIs e serviços > Credenciais**.
2. Clique em **Criar credenciais > ID do cliente OAuth**.
3. Tipo de aplicativo: **Aplicativo da Web**.
4. Nome: `Portal MSE - KPI Hitachi` (só um rótulo, pode ser qualquer nome).
5. Em **Origens JavaScript autorizadas**, clique em **Adicionar URI** e cole
   exatamente a URL que você anotou no Passo 1, por exemplo:

   ```
   https://SEU-APP.streamlit.app
   ```

   Sem barra no final, sem caminho depois do domínio.
6. Não precisa preencher "URIs de redirecionamento autorizados" para este
   fluxo. Clique em **Criar**.
7. O Google vai mostrar o **Client ID** (uma string terminando em
   `.apps.googleusercontent.com`). Copie esse valor.

## Passo 6 — Cole o Client ID nos Secrets do Streamlit

1. No Streamlit Cloud, abra **App settings > Secrets** do seu app.
2. Adicione (ou edite) estas duas linhas:

   ```toml
   google_drive_client_id = "COLE-AQUI-O-CLIENT-ID.apps.googleusercontent.com"
   google_drive_root_folder_id = "1LyjXgkF9p9TrWH39TbKly0oCG7HXNfRc"
   ```

   (o `google_drive_root_folder_id` já vem preenchido com a pasta do link que
   você passou — só troque se quiser apontar para outra pasta raiz.)
3. Salve. O Streamlit reinicia o app sozinho em alguns segundos.

## Passo 7 — Conecte pelo portal

1. Abra o portal, vá em **KPI Hitachi > Cadastro**.
2. Na seção **Importar documentos dos colaboradores**, você vai ver o bloco
   **Envio automático para o Google Drive** com o botão **Conectar Google
   Drive**.
3. Clique nele. O Google vai abrir uma janela pedindo para você entrar com a
   conta autorizada (a mesma que você cadastrou como usuária de teste no
   Passo 4) e confirmar o acesso ao Drive.
4. Depois de autorizar, o status muda para "Google Drive conectado". A partir
   daí, todo documento que ficar **OK** — seja pela busca automática na API,
   pela importação manual, ou por uma troca de status manual — é enviado
   sozinho para a pasta certa.

## Perguntas comuns

**Preciso clicar em "Conectar" toda vez que abrir o portal?**
A autorização vale por um tempo dentro daquela sessão do navegador (cerca de
1 hora, renovada automaticamente enquanto a aba ficar aberta). Se passar
muito tempo ou você fechar o navegador, pode pedir para conectar de novo.

**E se eu esquecer de conectar antes de importar documentos?**
Sem problema: os documentos continuam sendo processados e marcados como OK
normalmente. Eles só não vão para o Drive até você clicar em "Conectar
Google Drive" — assim que conectar, o portal varre todos os colaboradores e
envia de uma vez qualquer holerite/cartão ponto que já esteja OK e ainda não
tenha sido salvo no Drive. Depois disso, os próximos que ficarem OK são
enviados automaticamente, sem precisar clicar em nada.

**Por que a pasta da competência tem uma barra no nome, tipo "07/2026"?**
O Google Drive aceita barra `/` no nome de uma pasta (não é tratado como
separador de caminho, é só um caractere no nome). Vai aparecer certinho no
site do Drive. Se você sincronizar essa pasta com o Google Drive para
Desktop no Windows/Mac, o aplicativo de sincronização troca a barra por um
caractere parecido no disco local (isso é uma particularidade do app de
sincronização, não do Drive em si). Se preferir evitar isso, me avise que eu
troco o formato da pasta para `2026-07` ou `Julho 2026`.
