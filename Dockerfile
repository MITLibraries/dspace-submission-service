FROM python:3.9-slim
RUN pip install --no-cache-dir --upgrade pip pipenv

WORKDIR /app
COPY . .

RUN pipenv install --system --clear --deploy

ENTRYPOINT ["python","submitter/cli.py"]
CMD ["--help"]
