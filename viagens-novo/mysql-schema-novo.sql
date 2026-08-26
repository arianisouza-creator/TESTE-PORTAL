-- Tabelas novas deste projeto (Portal MSE - Passagens unificado), para quando
-- for rodar contra o MySQL de producao (DATABASE_URL=mysql+pymysql://...).
-- As tabelas antigas (passagens_rows, passagens_complements, etc.) sao as
-- mesmas do Portal-Passagens atual - ver mysql-schema.sql daquele projeto.

SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS passagens_solicitacoes (
  id VARCHAR(64) NOT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'pendente',
  cotar_passagem TINYINT(1) NOT NULL DEFAULT 0,
  nome_colaborador VARCHAR(255) NOT NULL DEFAULT '',
  obra VARCHAR(255) NOT NULL DEFAULT '',
  tipo_passagem VARCHAR(64) NOT NULL DEFAULT '',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  dados JSON NOT NULL,
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS passagens_cotacoes_resultado (
  id VARCHAR(64) NOT NULL,
  solicitacao_id VARCHAR(64) NOT NULL,
  companhia VARCHAR(32) NOT NULL DEFAULT '',
  status VARCHAR(32) NOT NULL DEFAULT '',
  mensagem_erro TEXT NULL,
  quote JSON NULL,
  aprovada TINYINT(1) NOT NULL DEFAULT 0,
  criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_cotacoes_solicitacao (solicitacao_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Cache do status de pedidos consultados na API de Pedidos (portalmse.com.br)
-- - preenchido pelo botao "Sincronizar API de Pedidos" do Dashboard, pra
-- mostrar o status ja na tabela sem precisar clicar linha a linha.
CREATE TABLE IF NOT EXISTS passagens_pedidos_status (
  numero_pedido VARCHAR(64) NOT NULL,
  status_pedido VARCHAR(64) NOT NULL DEFAULT '',
  fornecedor VARCHAR(255) NOT NULL DEFAULT '',
  obra VARCHAR(255) NOT NULL DEFAULT '',
  valor DECIMAL(12,2) NULL,
  data_pedido VARCHAR(32) NOT NULL DEFAULT '',
  data_entrega VARCHAR(32) NOT NULL DEFAULT '',
  tipo_descricao VARCHAR(255) NOT NULL DEFAULT '',
  atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (numero_pedido)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS passagens_fechamentos_fatura (
  id VARCHAR(64) NOT NULL,
  data JSON NOT NULL,
  criado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS passagens_fatura_rascunhos (
  id VARCHAR(64) NOT NULL,
  data JSON NOT NULL,
  atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
