FROM python:3-slim-bookworm
LABEL authors="Bury"

WORKDIR /src

COPY mainV2.py /src/main.py
COPY requirements.txt /src

RUN pip install -r /src/requirements.txt

# 👇 here we set the user
#USER user

ENTRYPOINT ["python3", "main.py"]