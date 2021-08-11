FROM python:3.9-slim
RUN pip install --no-cache-dir pipenv

WORKDIR /app
COPY . .

RUN pipenv install --system --ignore-pipfile --clear --deploy

ENTRYPOINT ["submitter"]
CMD ["--help"]
