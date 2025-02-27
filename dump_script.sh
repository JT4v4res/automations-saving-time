#!/bin/bash

export PGPASSWORD="<pg_password>"
DATABASE="<db_name>"
USER="<db_user>"
HOST="<db_host>"
TABLE_PREFIX="<your_table_prefix>"
OUTPUT_DIR="<your_output_dir>"

# Garante que o diretório de saída existe
mkdir -p "$OUTPUT_DIR"

MONTHS=("03" "04" "05" "06" "07" "08" "09" "10" "11" "12" "01" "02")
YEARS=("2024" "2024" "2024" "2024" "2024" "2024" "2024" "2024" "2024" "2024" "2025" "2025")

echo "💾 Espaço em disco antes do processo:"
df -h | grep "/mnt/c"

for i in "${!MONTHS[@]}"; do
    MES="${MONTHS[$i]}"
    ANO="${YEARS[$i]}"
    DATA="${ANO}-${MES}-01"
    NEXT_MONTH=$(date -d "$DATA +1 month" +"%Y-%m-%d")
    DUMP_FILE="$OUTPUT_DIR/dump_${MES}_${ANO}.dump"

    # Verifica se o dump já existe
    if [ -f "$DUMP_FILE" ]; then
        echo "⚠️  Dump para $ANO-$MES já existe, pulando..."
        continue
    fi

    echo "🚀 Processando dump para $ANO-$MES..."

    # Criar tabelas temporárias
    psql -U $USER -h $HOST -d $DATABASE -c "
    CREATE TABLE IF NOT EXISTS contacts_${MES}_${ANO} AS
    SELECT * FROM ${TABLE_PREFIX}_contacts WHERE created_on >= '$DATA' AND created_on < '$NEXT_MONTH';

    CREATE TABLE IF NOT EXISTS contacts_eav_${MES}_${ANO} AS
    SELECT ce.* FROM ${TABLE_PREFIX}_contacts_eav ce
    JOIN ${TABLE_PREFIX}_contacts c ON ce.contact_uuid = c.uuid
    WHERE c.created_on >= '$DATA' AND c.created_on < '$NEXT_MONTH';

    CREATE TABLE IF NOT EXISTS messages_${MES}_${ANO} AS
    SELECT * FROM ${TABLE_PREFIX}_messages WHERE sent_on >= '$DATA' AND sent_on < '$NEXT_MONTH';

    CREATE TABLE IF NOT EXISTS runs_${MES}_${ANO} AS
    SELECT * FROM ${TABLE_PREFIX}_runs WHERE created_on >= '$DATA' AND created_on < '$NEXT_MONTH';

    CREATE TABLE IF NOT EXISTS runs_values_${MES}_${ANO} AS
    SELECT rv.* FROM ${TABLE_PREFIX}_runs_values rv
    JOIN ${TABLE_PREFIX}_runs r ON rv.runs_uuid = r.uuid
    WHERE r.created_on >= '$DATA' AND r.created_on < '$NEXT_MONTH';
    "

    echo "✅ Tabelas temporárias criadas para $ANO-$MES!"

    # Realizar o dump
    pg_dump -U $USER -h $HOST -d $DATABASE \
        --table=contacts_${MES}_${ANO} \
        --table=contacts_eav_${MES}_${ANO} \
        --table=messages_${MES}_${ANO} \
        --table=runs_${MES}_${ANO} \
        --table=runs_values_${MES}_${ANO} \
        --column-inserts \
        -F c -f "$DUMP_FILE"

    if [ $? -eq 0 ]; then
        echo "✅ Dump gerado com sucesso: $DUMP_FILE"

        # Removendo os dados já salvos no dump das tabelas originais
        echo "🗑 Removendo dados antigos de $ANO-$MES das tabelas originais..."
        psql -U $USER -h $HOST -d $DATABASE -c "
        DELETE FROM ${TABLE_PREFIX}_contacts WHERE created_on >= '$DATA' AND created_on < '$NEXT_MONTH';
        DELETE FROM ${TABLE_PREFIX}_contacts_eav WHERE contact_uuid IN
            (SELECT uuid FROM ${TABLE_PREFIX}_contacts WHERE created_on >= '$DATA' AND created_on < '$NEXT_MONTH');
        DELETE FROM ${TABLE_PREFIX}_messages WHERE sent_on >= '$DATA' AND sent_on < '$NEXT_MONTH';
        DELETE FROM ${TABLE_PREFIX}_runs WHERE created_on >= '$DATA' AND created_on < '$NEXT_MONTH';
        DELETE FROM ${TABLE_PREFIX}_runs_values WHERE runs_uuid IN
            (SELECT uuid FROM ${TABLE_PREFIX}_runs WHERE created_on >= '$DATA' AND created_on < '$NEXT_MONTH');
        "
        echo "✅ Dados removidos das tabelas originais para $ANO-$MES!"

        echo "🚀 Executando VACUUM para liberar espaço..."
        psql -U $USER -h $HOST -d $DATABASE -c "
        VACUUM FULL ANALYZE VERBOSE contacts_${MES}_${ANO},
                    contacts_eav_${MES}_${ANO},
                    messages_${MES}_${ANO},
                    runs_${MES}_${ANO},
                    runs_values_${MES}_${ANO},
                    ${TABLE_PREFIX}_contacts,
                    ${TABLE_PREFIX}_contacts_eav,
                    ${TABLE_PREFIX}_messages,
                    ${TABLE_PREFIX}_runs,
                    ${TABLE_PREFIX}_runs_values;
        "
        echo "✅ VACUUM concluído! Espaço liberado no SSD."

        # Remove tabelas temporárias para liberar espaço
        echo "🗑 Removendo tabelas temporárias para $ANO-$MES..."
        psql -U $USER -h $HOST -d $DATABASE -c "
        TRUNCATE TABLE IF EXISTS contacts_${MES}_${ANO} CONTINUE IDENTITY;
        TRUNCATE TABLE IF EXISTS contacts_eav_${MES}_${ANO} CONTINUE IDENTITY;
        TRUNCATE TABLE IF EXISTS messages_${MES}_${ANO} CONTINUE IDENTITY;
        TRUNCATE TABLE IF EXISTS runs_${MES}_${ANO} CONTINUE IDENTITY;
        TRUNCATE TABLE IF EXISTS runs_values_${MES}_${ANO} CONTINUE IDENTITY;
        "
        echo "✅ Tabelas temporárias removidas para $ANO-$MES!"
    else
        echo "❌ ERRO: Falha ao gerar dump para $ANO-$MES!"
    fi

    echo "💾 Espaço em disco após o Dump:"
    df -h | grep "/mnt/c"
done

echo "✅ Todos os dumps foram finalizados com sucesso! 🚀"
