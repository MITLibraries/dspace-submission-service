FROM python:3.9-slim as build
WORKDIR /app
COPY . .
RUN cd /app && python setup.py bdist_wheel


FROM python:3.9-slim
ENV PIP_NO_CACHE_DIR yes
WORKDIR /app
RUN pip install --no-cache-dir --upgrade pip pipenv

COPY Pipfile* /
RUN pipenv install --system --clear --deploy

COPY --from=build /app/dist/submitter-*-py3-none-any.whl .
RUN pip install submitter-*-py3-none-any.whl

ENTRYPOINT ["submitter"]
