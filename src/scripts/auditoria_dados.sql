\pset footer off

\echo '===== 1. CAGED: registros e totais por competência ====='
SELECT competencia,
       COUNT(*) AS setores,
       SUM(admissoes) AS admissoes,
       SUM(demissoes) AS demissoes,
       SUM(saldo) AS saldo
FROM caged_movimentacao
GROUP BY competencia
ORDER BY competencia;

\echo '===== 2. CAGED: linhas com problema (esperado: 0) ====='
SELECT
    COUNT(*) FILTER (WHERE competencia !~ '^[0-9]{4}-[0-9]{2}$') AS competencia_formato_invalido,
    COUNT(*) FILTER (WHERE setor IS NULL OR TRIM(setor) = '') AS setor_vazio,
    COUNT(*) FILTER (WHERE admissoes < 0 OR demissoes < 0) AS valores_negativos,
    COUNT(*) FILTER (WHERE saldo <> admissoes - demissoes) AS saldo_inconsistente
FROM caged_movimentacao;

\echo '===== 3. CEMPRE: registros por ano ====='
SELECT ano,
       COUNT(*) AS setores,
       COUNT(*) FILTER (WHERE pessoal_ocupado IS NULL) AS sem_pessoal_ocupado,
       COUNT(*) FILTER (WHERE salario_medio IS NULL) AS sem_salario_medio
FROM cempre_emprego
GROUP BY ano
ORDER BY ano;

\echo '===== 4. CEMPRE: linhas com problema (esperado: 0) ====='
SELECT
    COUNT(*) FILTER (WHERE ano !~ '^[0-9]{4}$') AS ano_formato_invalido,
    COUNT(*) FILTER (WHERE setor IS NULL OR TRIM(setor) = '') AS setor_vazio,
    COUNT(*) FILTER (WHERE unidades_locais < 0 OR pessoal_ocupado < 0 OR salario_medio < 0) AS valores_negativos
FROM cempre_emprego;

\echo '===== 5. RFB: registros e totais por competência ====='
SELECT competencia,
       COUNT(*) AS setores,
       SUM(ativas) AS ativas,
       SUM(aberturas) AS aberturas,
       SUM(encerramentos) AS encerramentos,
       SUM(ativas_mei) AS ativas_mei,
       SUM(ativas_simples) AS ativas_simples
FROM rfb_empresas
GROUP BY competencia
ORDER BY competencia;

\echo '===== 6. RFB: linhas com problema (esperado: 0) ====='
SELECT
    COUNT(*) FILTER (WHERE competencia !~ '^[0-9]{4}-[0-9]{2}$') AS competencia_formato_invalido,
    COUNT(*) FILTER (WHERE setor IS NULL OR TRIM(setor) = '') AS setor_vazio,
    COUNT(*) FILTER (WHERE ativas < 0 OR aberturas < 0 OR encerramentos < 0) AS valores_negativos,
    COUNT(*) FILTER (WHERE ativas_mei > ativas OR ativas_simples > ativas) AS subtotal_maior_que_total
FROM rfb_empresas;

\echo '===== 7. Estrutura: tabelas, índice e migration ====='
SELECT tablename AS tabela FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;
SELECT indexname AS indice_caged FROM pg_indexes WHERE tablename = 'caged_movimentacao' ORDER BY indexname;
SELECT version_num AS migration_atual FROM alembic_version;
