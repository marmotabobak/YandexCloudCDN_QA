# Yandex Cloud CDN API Processor

Service communicates with Yandex Cloud CDN through REST API to support it's basic functionality such as creation, modifying and deleting origins and CDN resources.

## Features
1. Yandex Cloud authorization
2. Origins management
3. CDN resources managements

## Installation
- python3.8 required
- clone repository
- install packet: ```pip install .```
- install requirements: ```pip install -r requirements.txt```
- get Yandex Cloud OAUTH-token and put it to ```OAUTH``` env
- create ```config.yaml```

## Known Yandex Cloud CND API bugs
- allows to create yccdn cdn-resource with same cname with following crash of such resource

## Testing
```pytest -o log_cli=true --log-cli-level=INFO```
