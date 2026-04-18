# COmandos uteis para a planilha

https://docs.google.com/spreadsheets/d/1zXzm7tlMV8iVPSd5pAoMAyYrd18AVhRUNrjmogDvD20/edit?usp=sharing

```
git log --tags --simplify-by-decoration --pretty="format:%ai %d" | head -20 
```


Mostra os últimos commits de um repositório

```
git checkout <tag> 
``` 
faz o checkout a partir dos commits, a tag pode ser algo como v2.4.8, listadas no comando anterior

```
git rev-parse HEAD
```

mostra o COMMIT SHA (da coluna commit_sha)

```
git log -1 --pretty=format:"%ai"
```
Data do commit da tag (coluna commit_data)

```
git log -1 --pretty=format:"%ad" --date=short
```
Dá a data do commit atualmente checkout. Formato ISO com timezone. 

```
git log --reverse --pretty=format:"%ad" --date=short | head -1
```
Data do primeiro commit do projeto (para calcular idade)

```
git shortlog -sn HEAD | wc -l
```
Número de contribuidores até o commit atual (coluna contribuidores)

```
git ls-files | xargs wc -l 2>/dev/null | tail -1
```
LOC total por contagem bruta (estimativa rápida, não precisa)

```
curl -u <token>: "http://localhost:9000/api/measures/component?component=<projectKey>&metricKeys=ncloc,ncloc_language_distribution"
```
LOC Java preciso (depois que o Sonar rodar) — pega do dashboard do SonarQube ou via API

```
git log --tags --simplify-by-decoration --pretty="format:%ai %d" | head -30
```
Lista de tags com datas (para escolher a tag)

```
git rev-list --count HEAD
```
Número de commits totais até a tag (métrica de atividade, opcional mas útil)

```
git log origin/main -1 --pretty=format:"%ai" 2>/dev/null || \
git log origin/master -1 --pretty=format:"%ai"
```
Último commit do branch principal (para decidir se o projeto está vivo)