FROM pgvector/pgvector:pg15

# Cargamos migraciones dentro de la imagen para no depender de bind mounts
# y ejecutarlas siempre en orden determinista.
COPY migrations /docker-seed/migrations
COPY init/00-run-migrations.sh /docker-entrypoint-initdb.d/00-run-migrations.sh
RUN chmod +x /docker-entrypoint-initdb.d/00-run-migrations.sh
