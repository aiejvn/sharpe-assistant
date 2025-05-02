FROM python:3.12-slim

COPY ./server /server

WORKDIR /server

RUN pip install --upgrade pip

RUN pip install -r requirements.txt

ENTRYPOINT [ "python" ]

CMD ["app.py"]