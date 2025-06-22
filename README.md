# fiveschan_webchat_distribuidos.
FivesChan - Sala de Chat em Tempo Real com Flask e Socket.IO

FivesChan é uma aplicação web de chat em tempo real que permite a comunicação instantânea entre múltiplos usuários em salas privadas. O sistema possibilita a criação de novas salas com um código de acesso único gerado automaticamente, ou a entrada em salas já existentes, garantindo um ambiente de bate-papo dinâmico e funcional.

O projeto foi construído sobre uma base de tecnologias modernas e eficientes. O backend é desenvolvido em Python com o microframework Flask, que gerencia as rotas e a estrutura da aplicação. A comunicação em tempo real é a principal funcionalidade, implementada com a biblioteca Flask-SocketIO, que utiliza WebSockets para permitir a troca de mensagens instantânea sem a necessidade de recarregar a página.

Para o ambiente de produção, o servidor é otimizado com Gunicorn e Gevent, que permitem o gerenciamento de múltiplas conexões simultâneas de forma assíncrona. O frontend é construído com HTML, CSS e JavaScript padrão
