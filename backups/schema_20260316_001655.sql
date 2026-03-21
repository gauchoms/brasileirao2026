--
-- PostgreSQL database dump
--

\restrict YbeRPjdIiyScvTH828s0dm1RQj6dC6I0zx6ilpFHCrud2gKD9KF4lgagHQrxRKB

-- Dumped from database version 18.1 (Debian 18.1-1.pgdg12+2)
-- Dumped by pg_dump version 18.3

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: public; Type: SCHEMA; Schema: -; Owner: brasileirao2026
--

-- *not* creating schema, since initdb creates it


ALTER SCHEMA public OWNER TO brasileirao2026;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: avatar_sugerido; Type: TABLE; Schema: public; Owner: brasileirao2026
--

CREATE TABLE public.avatar_sugerido (
    id integer NOT NULL,
    url character varying(200) NOT NULL,
    categoria character varying(50) NOT NULL
);


ALTER TABLE public.avatar_sugerido OWNER TO brasileirao2026;

--
-- Name: avatar_sugerido_id_seq; Type: SEQUENCE; Schema: public; Owner: brasileirao2026
--

CREATE SEQUENCE public.avatar_sugerido_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.avatar_sugerido_id_seq OWNER TO brasileirao2026;

--
-- Name: avatar_sugerido_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: brasileirao2026
--

ALTER SEQUENCE public.avatar_sugerido_id_seq OWNED BY public.avatar_sugerido.id;


--
-- Name: bolao; Type: TABLE; Schema: public; Owner: brasileirao2026
--

CREATE TABLE public.bolao (
    id integer NOT NULL,
    nome character varying(100) NOT NULL,
    competicao_id integer,
    dono_id integer NOT NULL,
    codigo_convite character varying(10) NOT NULL,
    regra_pontuacao_id integer NOT NULL,
    tipo_acesso character varying(20),
    status_pagamento character varying(20),
    valor_pago double precision,
    data_pagamento timestamp without time zone,
    status character varying(20),
    data_criacao timestamp without time zone,
    tipo_bolao character varying(30) DEFAULT 'campeonato_completo'::character varying,
    time_especifico_id integer,
    ano integer
);


ALTER TABLE public.bolao OWNER TO brasileirao2026;

--
-- Name: bolao_id_seq; Type: SEQUENCE; Schema: public; Owner: brasileirao2026
--

CREATE SEQUENCE public.bolao_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.bolao_id_seq OWNER TO brasileirao2026;

--
-- Name: bolao_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: brasileirao2026
--

ALTER SEQUENCE public.bolao_id_seq OWNED BY public.bolao.id;


--
-- Name: chat; Type: TABLE; Schema: public; Owner: brasileirao2026
--

CREATE TABLE public.chat (
    id integer NOT NULL,
    bolao_id integer NOT NULL,
    tipo character varying(20),
    jogo_id integer
);


ALTER TABLE public.chat OWNER TO brasileirao2026;

--
-- Name: chat_id_seq; Type: SEQUENCE; Schema: public; Owner: brasileirao2026
--

CREATE SEQUENCE public.chat_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.chat_id_seq OWNER TO brasileirao2026;

--
-- Name: chat_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: brasileirao2026
--

ALTER SEQUENCE public.chat_id_seq OWNED BY public.chat.id;


--
-- Name: competicao; Type: TABLE; Schema: public; Owner: brasileirao2026
--

CREATE TABLE public.competicao (
    id integer NOT NULL,
    nome character varying(100) NOT NULL,
    ano integer NOT NULL,
    tipo character varying(50) NOT NULL,
    api_league_id integer,
    uso character varying(20) DEFAULT 'ambos'::character varying,
    disponivel_dashboard boolean DEFAULT false
);


ALTER TABLE public.competicao OWNER TO brasileirao2026;

--
-- Name: competicao_id_seq; Type: SEQUENCE; Schema: public; Owner: brasileirao2026
--

CREATE SEQUENCE public.competicao_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.competicao_id_seq OWNER TO brasileirao2026;

--
-- Name: competicao_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: brasileirao2026
--

ALTER SEQUENCE public.competicao_id_seq OWNED BY public.competicao.id;


--
-- Name: jogo; Type: TABLE; Schema: public; Owner: brasileirao2026
--

CREATE TABLE public.jogo (
    id integer NOT NULL,
    api_id integer NOT NULL,
    rodada character varying(50) NOT NULL,
    time_casa_id integer NOT NULL,
    time_fora_id integer NOT NULL,
    data character varying(50),
    gols_casa integer,
    gols_fora integer,
    competicao_id integer
);


ALTER TABLE public.jogo OWNER TO brasileirao2026;

--
-- Name: jogo_id_seq; Type: SEQUENCE; Schema: public; Owner: brasileirao2026
--

CREATE SEQUENCE public.jogo_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.jogo_id_seq OWNER TO brasileirao2026;

--
-- Name: jogo_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: brasileirao2026
--

ALTER SEQUENCE public.jogo_id_seq OWNED BY public.jogo.id;


--
-- Name: mensagem; Type: TABLE; Schema: public; Owner: brasileirao2026
--

CREATE TABLE public.mensagem (
    id integer NOT NULL,
    chat_id integer NOT NULL,
    usuario_id integer NOT NULL,
    texto text NOT NULL,
    data_envio timestamp without time zone,
    editada boolean,
    deletada boolean
);


ALTER TABLE public.mensagem OWNER TO brasileirao2026;

--
-- Name: mensagem_id_seq; Type: SEQUENCE; Schema: public; Owner: brasileirao2026
--

CREATE SEQUENCE public.mensagem_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.mensagem_id_seq OWNER TO brasileirao2026;

--
-- Name: mensagem_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: brasileirao2026
--

ALTER SEQUENCE public.mensagem_id_seq OWNED BY public.mensagem.id;


--
-- Name: meta; Type: TABLE; Schema: public; Owner: brasileirao2026
--

CREATE TABLE public.meta (
    id integer NOT NULL,
    time_id integer NOT NULL,
    descricao character varying(50) NOT NULL,
    pontos_alvo integer NOT NULL
);


ALTER TABLE public.meta OWNER TO brasileirao2026;

--
-- Name: meta_id_seq; Type: SEQUENCE; Schema: public; Owner: brasileirao2026
--

CREATE SEQUENCE public.meta_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.meta_id_seq OWNER TO brasileirao2026;

--
-- Name: meta_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: brasileirao2026
--

ALTER SEQUENCE public.meta_id_seq OWNED BY public.meta.id;


--
-- Name: notificacao; Type: TABLE; Schema: public; Owner: brasileirao2026
--

CREATE TABLE public.notificacao (
    id integer NOT NULL,
    usuario_id integer NOT NULL,
    tipo character varying(50) NOT NULL,
    mensagem character varying(200) NOT NULL,
    lida boolean,
    data timestamp without time zone
);


ALTER TABLE public.notificacao OWNER TO brasileirao2026;

--
-- Name: notificacao_id_seq; Type: SEQUENCE; Schema: public; Owner: brasileirao2026
--

CREATE SEQUENCE public.notificacao_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.notificacao_id_seq OWNER TO brasileirao2026;

--
-- Name: notificacao_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: brasileirao2026
--

ALTER SEQUENCE public.notificacao_id_seq OWNED BY public.notificacao.id;


--
-- Name: palpite; Type: TABLE; Schema: public; Owner: brasileirao2026
--

CREATE TABLE public.palpite (
    id integer NOT NULL,
    bolao_id integer NOT NULL,
    usuario_id integer NOT NULL,
    jogo_id integer NOT NULL,
    gols_casa_palpite integer NOT NULL,
    gols_fora_palpite integer NOT NULL,
    pontos_obtidos integer,
    data_palpite timestamp without time zone,
    hash_comprovante character varying(64),
    timestamp_preciso bigint
);


ALTER TABLE public.palpite OWNER TO brasileirao2026;

--
-- Name: palpite_id_seq; Type: SEQUENCE; Schema: public; Owner: brasileirao2026
--

CREATE SEQUENCE public.palpite_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.palpite_id_seq OWNER TO brasileirao2026;

--
-- Name: palpite_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: brasileirao2026
--

ALTER SEQUENCE public.palpite_id_seq OWNED BY public.palpite.id;


--
-- Name: participante_bolao; Type: TABLE; Schema: public; Owner: brasileirao2026
--

CREATE TABLE public.participante_bolao (
    id integer NOT NULL,
    bolao_id integer NOT NULL,
    usuario_id integer NOT NULL,
    data_entrada timestamp without time zone,
    pontos_totais integer
);


ALTER TABLE public.participante_bolao OWNER TO brasileirao2026;

--
-- Name: participante_bolao_id_seq; Type: SEQUENCE; Schema: public; Owner: brasileirao2026
--

CREATE SEQUENCE public.participante_bolao_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.participante_bolao_id_seq OWNER TO brasileirao2026;

--
-- Name: participante_bolao_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: brasileirao2026
--

ALTER SEQUENCE public.participante_bolao_id_seq OWNED BY public.participante_bolao.id;


--
-- Name: projecao; Type: TABLE; Schema: public; Owner: brasileirao2026
--

CREATE TABLE public.projecao (
    id integer NOT NULL,
    jogo_id integer NOT NULL,
    time_id integer NOT NULL,
    tipo character varying(20) NOT NULL,
    pontos integer
);


ALTER TABLE public.projecao OWNER TO brasileirao2026;

--
-- Name: projecao_id_seq; Type: SEQUENCE; Schema: public; Owner: brasileirao2026
--

CREATE SEQUENCE public.projecao_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.projecao_id_seq OWNER TO brasileirao2026;

--
-- Name: projecao_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: brasileirao2026
--

ALTER SEQUENCE public.projecao_id_seq OWNED BY public.projecao.id;


--
-- Name: provocacao; Type: TABLE; Schema: public; Owner: brasileirao2026
--

CREATE TABLE public.provocacao (
    id integer NOT NULL,
    de_usuario_id integer NOT NULL,
    para_usuario_id integer NOT NULL,
    bolao_id integer NOT NULL,
    texto character varying(200) NOT NULL,
    jogo_relacionado_id integer,
    data timestamp without time zone
);


ALTER TABLE public.provocacao OWNER TO brasileirao2026;

--
-- Name: provocacao_id_seq; Type: SEQUENCE; Schema: public; Owner: brasileirao2026
--

CREATE SEQUENCE public.provocacao_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.provocacao_id_seq OWNER TO brasileirao2026;

--
-- Name: provocacao_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: brasileirao2026
--

ALTER SEQUENCE public.provocacao_id_seq OWNED BY public.provocacao.id;


--
-- Name: reacao; Type: TABLE; Schema: public; Owner: brasileirao2026
--

CREATE TABLE public.reacao (
    id integer NOT NULL,
    mensagem_id integer NOT NULL,
    usuario_id integer NOT NULL,
    tipo character varying(10) NOT NULL
);


ALTER TABLE public.reacao OWNER TO brasileirao2026;

--
-- Name: reacao_id_seq; Type: SEQUENCE; Schema: public; Owner: brasileirao2026
--

CREATE SEQUENCE public.reacao_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.reacao_id_seq OWNER TO brasileirao2026;

--
-- Name: reacao_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: brasileirao2026
--

ALTER SEQUENCE public.reacao_id_seq OWNED BY public.reacao.id;


--
-- Name: regra_pontuacao; Type: TABLE; Schema: public; Owner: brasileirao2026
--

CREATE TABLE public.regra_pontuacao (
    id integer NOT NULL,
    nome character varying(100) NOT NULL,
    criador_id integer NOT NULL,
    pontos_placar_exato integer,
    pontos_resultado_certo integer,
    pontos_gols_time_casa integer,
    pontos_gols_time_fora integer,
    bonus_placar_perfeito integer,
    publica boolean,
    modo character varying(20) DEFAULT 'acertos_parciais'::character varying,
    pontos_gols_vencedor integer DEFAULT 0,
    pontos_gols_perdedor integer DEFAULT 0,
    pontos_diferenca_gols integer DEFAULT 0,
    ativar_bonus_gols boolean DEFAULT false,
    limite_gols_bonus integer DEFAULT 4,
    pontos_por_gol_extra integer DEFAULT 1,
    data_criacao timestamp without time zone,
    pontos_resultado integer DEFAULT 5,
    requer_resultado_correto boolean DEFAULT true
);


ALTER TABLE public.regra_pontuacao OWNER TO brasileirao2026;

--
-- Name: regra_pontuacao_id_seq; Type: SEQUENCE; Schema: public; Owner: brasileirao2026
--

CREATE SEQUENCE public.regra_pontuacao_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.regra_pontuacao_id_seq OWNER TO brasileirao2026;

--
-- Name: regra_pontuacao_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: brasileirao2026
--

ALTER SEQUENCE public.regra_pontuacao_id_seq OWNED BY public.regra_pontuacao.id;


--
-- Name: snapshot_pontuacao; Type: TABLE; Schema: public; Owner: brasileirao2026
--

CREATE TABLE public.snapshot_pontuacao (
    id integer NOT NULL,
    bolao_id integer NOT NULL,
    data_snapshot timestamp without time zone DEFAULT now(),
    motivo character varying(200),
    usuario_id integer,
    dados_json text NOT NULL
);


ALTER TABLE public.snapshot_pontuacao OWNER TO brasileirao2026;

--
-- Name: snapshot_pontuacao_id_seq; Type: SEQUENCE; Schema: public; Owner: brasileirao2026
--

CREATE SEQUENCE public.snapshot_pontuacao_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.snapshot_pontuacao_id_seq OWNER TO brasileirao2026;

--
-- Name: snapshot_pontuacao_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: brasileirao2026
--

ALTER SEQUENCE public.snapshot_pontuacao_id_seq OWNED BY public.snapshot_pontuacao.id;


--
-- Name: solicitacao_entrada; Type: TABLE; Schema: public; Owner: brasileirao2026
--

CREATE TABLE public.solicitacao_entrada (
    id integer NOT NULL,
    bolao_id integer NOT NULL,
    usuario_id integer NOT NULL,
    status character varying(20),
    data_solicitacao timestamp without time zone,
    data_resposta timestamp without time zone,
    respondido_por integer
);


ALTER TABLE public.solicitacao_entrada OWNER TO brasileirao2026;

--
-- Name: solicitacao_entrada_id_seq; Type: SEQUENCE; Schema: public; Owner: brasileirao2026
--

CREATE SEQUENCE public.solicitacao_entrada_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.solicitacao_entrada_id_seq OWNER TO brasileirao2026;

--
-- Name: solicitacao_entrada_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: brasileirao2026
--

ALTER SEQUENCE public.solicitacao_entrada_id_seq OWNED BY public.solicitacao_entrada.id;


--
-- Name: solicitacao_pagamento; Type: TABLE; Schema: public; Owner: brasileirao2026
--

CREATE TABLE public.solicitacao_pagamento (
    id integer NOT NULL,
    usuario_id integer NOT NULL,
    bolao_id integer,
    valor double precision NOT NULL,
    comprovante_url character varying(200),
    metodo_pagamento character varying(50),
    status character varying(20),
    data_solicitacao timestamp without time zone,
    data_aprovacao timestamp without time zone,
    aprovado_por integer,
    observacoes text,
    mercadopago_payment_id character varying(100)
);


ALTER TABLE public.solicitacao_pagamento OWNER TO brasileirao2026;

--
-- Name: solicitacao_pagamento_id_seq; Type: SEQUENCE; Schema: public; Owner: brasileirao2026
--

CREATE SEQUENCE public.solicitacao_pagamento_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.solicitacao_pagamento_id_seq OWNER TO brasileirao2026;

--
-- Name: solicitacao_pagamento_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: brasileirao2026
--

ALTER SEQUENCE public.solicitacao_pagamento_id_seq OWNED BY public.solicitacao_pagamento.id;


--
-- Name: time; Type: TABLE; Schema: public; Owner: brasileirao2026
--

CREATE TABLE public."time" (
    id integer NOT NULL,
    api_id integer NOT NULL,
    nome character varying(100) NOT NULL,
    logo_url character varying(200),
    pais character varying(50),
    liga_principal character varying(100),
    ativo boolean DEFAULT true,
    ultima_atualizacao timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public."time" OWNER TO brasileirao2026;

--
-- Name: time_id_seq; Type: SEQUENCE; Schema: public; Owner: brasileirao2026
--

CREATE SEQUENCE public.time_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.time_id_seq OWNER TO brasileirao2026;

--
-- Name: time_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: brasileirao2026
--

ALTER SEQUENCE public.time_id_seq OWNED BY public."time".id;


--
-- Name: usuario; Type: TABLE; Schema: public; Owner: brasileirao2026
--

CREATE TABLE public.usuario (
    id integer NOT NULL,
    username character varying(80) NOT NULL,
    password_hash character varying(200) NOT NULL,
    is_admin boolean,
    nome_completo character varying(200),
    email character varying(120),
    avatar_tipo character varying(20) DEFAULT 'sugerido'::character varying,
    avatar_sugerido_id integer,
    avatar_custom_url character varying(200),
    time_coracao_id integer,
    tipo character varying(20) DEFAULT 'participante'::character varying,
    status character varying(20) DEFAULT 'ativo'::character varying,
    data_cadastro timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    termos_aceitos_em timestamp without time zone
);


ALTER TABLE public.usuario OWNER TO brasileirao2026;

--
-- Name: usuario_id_seq; Type: SEQUENCE; Schema: public; Owner: brasileirao2026
--

CREATE SEQUENCE public.usuario_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.usuario_id_seq OWNER TO brasileirao2026;

--
-- Name: usuario_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: brasileirao2026
--

ALTER SEQUENCE public.usuario_id_seq OWNED BY public.usuario.id;


--
-- Name: avatar_sugerido id; Type: DEFAULT; Schema: public; Owner: brasileirao2026
--

ALTER TABLE ONLY public.avatar_sugerido ALTER COLUMN id SET DEFAULT nextval('public.avatar_sugerido_id_seq'::regclass);


--
-- Name: bolao id; Type: DEFAULT; Schema: public; Owner: brasileirao2026
--

ALTER TABLE ONLY public.bolao ALTER COLUMN id SET DEFAULT nextval('public.bolao_id_seq'::regclass);


--
-- Name: chat id; Type: DEFAULT; Schema: public; Owner: brasileirao2026
--

ALTER TABLE ONLY public.chat ALTER COLUMN id SET DEFAULT nextval('public.chat_id_seq'::regclass);


--
-- Name: competicao id; Type: DEFAULT; Schema: public; Owner: brasileirao2026
--

ALTER TABLE ONLY public.competicao ALTER COLUMN id SET DEFAULT nextval('public.competicao_id_seq'::regclass);


--
-- Name: jogo id; Type: DEFAULT; Schema: public; Owner: brasileirao2026
--

ALTER TABLE ONLY public.jogo ALTER COLUMN id SET DEFAULT nextval('public.jogo_id_seq'::regclass);


--
-- Name: mensagem id; Type: DEFAULT; Schema: public; Owner: brasileirao2026
--

ALTER TABLE ONLY public.mensagem ALTER COLUMN id SET DEFAULT nextval('public.mensagem_id_seq'::regclass);


--
-- Name: meta id; Type: DEFAULT; Schema: public; Owner: brasileirao2026
--

ALTER TABLE ONLY public.meta ALTER COLUMN id SET DEFAULT nextval('public.meta_id_seq'::regclass);


--
-- Name: notificacao id; Type: DEFAULT; Schema: public; Owner: brasileirao2026
--

ALTER TABLE ONLY public.notificacao ALTER COLUMN id SET DEFAULT nextval('public.notificacao_id_seq'::regclass);


--
-- Name: palpite id; Type: DEFAULT; Schema: public; Owner: brasileirao2026
--

ALTER TABLE ONLY public.palpite ALTER COLUMN id SET DEFAULT nextval('public.palpite_id_seq'::regclass);


--
-- Name: participante_bolao id; Type: DEFAULT; Schema: public; Owner: brasileirao2026
--

ALTER TABLE ONLY public.participante_bolao ALTER COLUMN id SET DEFAULT nextval('public.participante_bolao_id_seq'::regclass);


--
-- Name: projecao id; Type: DEFAULT; Schema: public; Owner: brasileirao2026
--

ALTER TABLE ONLY public.projecao ALTER COLUMN id SET DEFAULT nextval('public.projecao_id_seq'::regclass);


--
-- Name: provocacao id; Type: DEFAULT; Schema: public; Owner: brasileirao2026
--

ALTER TABLE ONLY public.provocacao ALTER COLUMN id SET DEFAULT nextval('public.provocacao_id_seq'::regclass);


--
-- Name: reacao id; Type: DEFAULT; Schema: public; Owner: brasileirao2026
--

ALTER TABLE ONLY public.reacao ALTER COLUMN id SET DEFAULT nextval('public.reacao_id_seq'::regclass);


--
-- Name: regra_pontuacao id; Type: DEFAULT; Schema: public; Owner: brasileirao2026
--

ALTER TABLE ONLY public.regra_pontuacao ALTER COLUMN id SET DEFAULT nextval('public.regra_pontuacao_id_seq'::regclass);


--
-- Name: snapshot_pontuacao id; Type: DEFAULT; Schema: public; Owner: brasileirao2026
--

ALTER TABLE ONLY public.snapshot_pontuacao ALTER COLUMN id SET DEFAULT nextval('public.snapshot_pontuacao_id_seq'::regclass);


--
-- Name: solicitacao_entrada id; Type: DEFAULT; Schema: public; Owner: brasileirao2026
--

ALTER TABLE ONLY public.solicitacao_entrada ALTER COLUMN id SET DEFAULT nextval('public.solicitacao_entrada_id_seq'::regclass);


--
-- Name: solicitacao_pagamento id; Type: DEFAULT; Schema: public; Owner: brasileirao2026
--

ALTER TABLE ONLY public.solicitacao_pagamento ALTER COLUMN id SET DEFAULT nextval('public.solicitacao_pagamento_id_seq'::regclass);


--
-- Name: time id; Type: DEFAULT; Schema: public; Owner: brasileirao2026
--

ALTER TABLE ONLY public."time" ALTER COLUMN id SET DEFAULT nextval('public.time_id_seq'::regclass);


--
-- Name: usuario id; Type: DEFAULT; Schema: public; Owner: brasileirao2026
--

ALTER TABLE ONLY public.usuario ALTER COLUMN id SET DEFAULT nextval('public.usuario_id_seq'::regclass);


--
-- Name: avatar_sugerido avatar_sugerido_pkey; Type: CONSTRAINT; Schema: public; Owner: brasileirao2026
--

ALTER TABLE ONLY public.avatar_sugerido
    ADD CONSTRAINT avatar_sugerido_pkey PRIMARY KEY (id);


--
-- Name: bolao bolao_codigo_convite_key; Type: CONSTRAINT; Schema: public; Owner: brasileirao2026
--

ALTER TABLE ONLY public.bolao
    ADD CONSTRAINT bolao_codigo_convite_key UNIQUE (codigo_convite);


--
-- Name: bolao bolao_pkey; Type: CONSTRAINT; Schema: public; Owner: brasileirao2026
--

ALTER TABLE ONLY public.bolao
    ADD CONSTRAINT bolao_pkey PRIMARY KEY (id);


--
-- Name: chat chat_pkey; Type: CONSTRAINT; Schema: public; Owner: brasileirao2026
--

ALTER TABLE ONLY public.chat
    ADD CONSTRAINT chat_pkey PRIMARY KEY (id);


--
-- Name: competicao competicao_pkey; Type: CONSTRAINT; Schema: public; Owner: brasileirao2026
--

ALTER TABLE ONLY public.competicao
    ADD CONSTRAINT competicao_pkey PRIMARY KEY (id);


--
-- Name: jogo jogo_api_id_key; Type: CONSTRAINT; Schema: public; Owner: brasileirao2026
--

ALTER TABLE ONLY public.jogo
    ADD CONSTRAINT jogo_api_id_key UNIQUE (api_id);


--
-- Name: jogo jogo_pkey; Type: CONSTRAINT; Schema: public; Owner: brasileirao2026
--

ALTER TABLE ONLY public.jogo
    ADD CONSTRAINT jogo_pkey PRIMARY KEY (id);


--
-- Name: mensagem mensagem_pkey; Type: CONSTRAINT; Schema: public; Owner: brasileirao2026
--

ALTER TABLE ONLY public.mensagem
    ADD CONSTRAINT mensagem_pkey PRIMARY KEY (id);


--
-- Name: meta meta_pkey; Type: CONSTRAINT; Schema: public; Owner: brasileirao2026
--

ALTER TABLE ONLY public.meta
    ADD CONSTRAINT meta_pkey PRIMARY KEY (id);


--
-- Name: notificacao notificacao_pkey; Type: CONSTRAINT; Schema: public; Owner: brasileirao2026
--

ALTER TABLE ONLY public.notificacao
    ADD CONSTRAINT notificacao_pkey PRIMARY KEY (id);


--
-- Name: palpite palpite_pkey; Type: CONSTRAINT; Schema: public; Owner: brasileirao2026
--

ALTER TABLE ONLY public.palpite
    ADD CONSTRAINT palpite_pkey PRIMARY KEY (id);


--
-- Name: participante_bolao participante_bolao_pkey; Type: CONSTRAINT; Schema: public; Owner: brasileirao2026
--

ALTER TABLE ONLY public.participante_bolao
    ADD CONSTRAINT participante_bolao_pkey PRIMARY KEY (id);


--
-- Name: projecao projecao_pkey; Type: CONSTRAINT; Schema: public; Owner: brasileirao2026
--

ALTER TABLE ONLY public.projecao
    ADD CONSTRAINT projecao_pkey PRIMARY KEY (id);


--
-- Name: provocacao provocacao_pkey; Type: CONSTRAINT; Schema: public; Owner: brasileirao2026
--

ALTER TABLE ONLY public.provocacao
    ADD CONSTRAINT provocacao_pkey PRIMARY KEY (id);


--
-- Name: reacao reacao_pkey; Type: CONSTRAINT; Schema: public; Owner: brasileirao2026
--

ALTER TABLE ONLY public.reacao
    ADD CONSTRAINT reacao_pkey PRIMARY KEY (id);


--
-- Name: regra_pontuacao regra_pontuacao_pkey; Type: CONSTRAINT; Schema: public; Owner: brasileirao2026
--

ALTER TABLE ONLY public.regra_pontuacao
    ADD CONSTRAINT regra_pontuacao_pkey PRIMARY KEY (id);


--
-- Name: snapshot_pontuacao snapshot_pontuacao_pkey; Type: CONSTRAINT; Schema: public; Owner: brasileirao2026
--

ALTER TABLE ONLY public.snapshot_pontuacao
    ADD CONSTRAINT snapshot_pontuacao_pkey PRIMARY KEY (id);


--
-- Name: solicitacao_entrada solicitacao_entrada_pkey; Type: CONSTRAINT; Schema: public; Owner: brasileirao2026
--

ALTER TABLE ONLY public.solicitacao_entrada
    ADD CONSTRAINT solicitacao_entrada_pkey PRIMARY KEY (id);


--
-- Name: solicitacao_pagamento solicitacao_pagamento_pkey; Type: CONSTRAINT; Schema: public; Owner: brasileirao2026
--

ALTER TABLE ONLY public.solicitacao_pagamento
    ADD CONSTRAINT solicitacao_pagamento_pkey PRIMARY KEY (id);


--
-- Name: time time_api_id_key; Type: CONSTRAINT; Schema: public; Owner: brasileirao2026
--

ALTER TABLE ONLY public."time"
    ADD CONSTRAINT time_api_id_key UNIQUE (api_id);


--
-- Name: time time_pkey; Type: CONSTRAINT; Schema: public; Owner: brasileirao2026
--

ALTER TABLE ONLY public."time"
    ADD CONSTRAINT time_pkey PRIMARY KEY (id);


--
-- Name: usuario usuario_pkey; Type: CONSTRAINT; Schema: public; Owner: brasileirao2026
--

ALTER TABLE ONLY public.usuario
    ADD CONSTRAINT usuario_pkey PRIMARY KEY (id);


--
-- Name: usuario usuario_username_key; Type: CONSTRAINT; Schema: public; Owner: brasileirao2026
--

ALTER TABLE ONLY public.usuario
    ADD CONSTRAINT usuario_username_key UNIQUE (username);


--
-- Name: idx_snapshot_bolao; Type: INDEX; Schema: public; Owner: brasileirao2026
--

CREATE INDEX idx_snapshot_bolao ON public.snapshot_pontuacao USING btree (bolao_id);


--
-- Name: bolao bolao_competicao_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brasileirao2026
--

ALTER TABLE ONLY public.bolao
    ADD CONSTRAINT bolao_competicao_id_fkey FOREIGN KEY (competicao_id) REFERENCES public.competicao(id);


--
-- Name: bolao bolao_dono_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brasileirao2026
--

ALTER TABLE ONLY public.bolao
    ADD CONSTRAINT bolao_dono_id_fkey FOREIGN KEY (dono_id) REFERENCES public.usuario(id);


--
-- Name: bolao bolao_regra_pontuacao_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brasileirao2026
--

ALTER TABLE ONLY public.bolao
    ADD CONSTRAINT bolao_regra_pontuacao_id_fkey FOREIGN KEY (regra_pontuacao_id) REFERENCES public.regra_pontuacao(id);


--
-- Name: chat chat_bolao_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brasileirao2026
--

ALTER TABLE ONLY public.chat
    ADD CONSTRAINT chat_bolao_id_fkey FOREIGN KEY (bolao_id) REFERENCES public.bolao(id);


--
-- Name: chat chat_jogo_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brasileirao2026
--

ALTER TABLE ONLY public.chat
    ADD CONSTRAINT chat_jogo_id_fkey FOREIGN KEY (jogo_id) REFERENCES public.jogo(id);


--
-- Name: jogo jogo_time_casa_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brasileirao2026
--

ALTER TABLE ONLY public.jogo
    ADD CONSTRAINT jogo_time_casa_id_fkey FOREIGN KEY (time_casa_id) REFERENCES public."time"(id);


--
-- Name: jogo jogo_time_fora_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brasileirao2026
--

ALTER TABLE ONLY public.jogo
    ADD CONSTRAINT jogo_time_fora_id_fkey FOREIGN KEY (time_fora_id) REFERENCES public."time"(id);


--
-- Name: mensagem mensagem_chat_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brasileirao2026
--

ALTER TABLE ONLY public.mensagem
    ADD CONSTRAINT mensagem_chat_id_fkey FOREIGN KEY (chat_id) REFERENCES public.chat(id);


--
-- Name: mensagem mensagem_usuario_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brasileirao2026
--

ALTER TABLE ONLY public.mensagem
    ADD CONSTRAINT mensagem_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES public.usuario(id);


--
-- Name: meta meta_time_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brasileirao2026
--

ALTER TABLE ONLY public.meta
    ADD CONSTRAINT meta_time_id_fkey FOREIGN KEY (time_id) REFERENCES public."time"(id);


--
-- Name: notificacao notificacao_usuario_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brasileirao2026
--

ALTER TABLE ONLY public.notificacao
    ADD CONSTRAINT notificacao_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES public.usuario(id);


--
-- Name: palpite palpite_bolao_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brasileirao2026
--

ALTER TABLE ONLY public.palpite
    ADD CONSTRAINT palpite_bolao_id_fkey FOREIGN KEY (bolao_id) REFERENCES public.bolao(id);


--
-- Name: palpite palpite_jogo_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brasileirao2026
--

ALTER TABLE ONLY public.palpite
    ADD CONSTRAINT palpite_jogo_id_fkey FOREIGN KEY (jogo_id) REFERENCES public.jogo(id);


--
-- Name: palpite palpite_usuario_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brasileirao2026
--

ALTER TABLE ONLY public.palpite
    ADD CONSTRAINT palpite_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES public.usuario(id);


--
-- Name: participante_bolao participante_bolao_bolao_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brasileirao2026
--

ALTER TABLE ONLY public.participante_bolao
    ADD CONSTRAINT participante_bolao_bolao_id_fkey FOREIGN KEY (bolao_id) REFERENCES public.bolao(id);


--
-- Name: participante_bolao participante_bolao_usuario_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brasileirao2026
--

ALTER TABLE ONLY public.participante_bolao
    ADD CONSTRAINT participante_bolao_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES public.usuario(id);


--
-- Name: projecao projecao_jogo_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brasileirao2026
--

ALTER TABLE ONLY public.projecao
    ADD CONSTRAINT projecao_jogo_id_fkey FOREIGN KEY (jogo_id) REFERENCES public.jogo(id);


--
-- Name: projecao projecao_time_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brasileirao2026
--

ALTER TABLE ONLY public.projecao
    ADD CONSTRAINT projecao_time_id_fkey FOREIGN KEY (time_id) REFERENCES public."time"(id);


--
-- Name: provocacao provocacao_bolao_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brasileirao2026
--

ALTER TABLE ONLY public.provocacao
    ADD CONSTRAINT provocacao_bolao_id_fkey FOREIGN KEY (bolao_id) REFERENCES public.bolao(id);


--
-- Name: provocacao provocacao_de_usuario_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brasileirao2026
--

ALTER TABLE ONLY public.provocacao
    ADD CONSTRAINT provocacao_de_usuario_id_fkey FOREIGN KEY (de_usuario_id) REFERENCES public.usuario(id);


--
-- Name: provocacao provocacao_jogo_relacionado_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brasileirao2026
--

ALTER TABLE ONLY public.provocacao
    ADD CONSTRAINT provocacao_jogo_relacionado_id_fkey FOREIGN KEY (jogo_relacionado_id) REFERENCES public.jogo(id);


--
-- Name: provocacao provocacao_para_usuario_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brasileirao2026
--

ALTER TABLE ONLY public.provocacao
    ADD CONSTRAINT provocacao_para_usuario_id_fkey FOREIGN KEY (para_usuario_id) REFERENCES public.usuario(id);


--
-- Name: reacao reacao_mensagem_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brasileirao2026
--

ALTER TABLE ONLY public.reacao
    ADD CONSTRAINT reacao_mensagem_id_fkey FOREIGN KEY (mensagem_id) REFERENCES public.mensagem(id);


--
-- Name: reacao reacao_usuario_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brasileirao2026
--

ALTER TABLE ONLY public.reacao
    ADD CONSTRAINT reacao_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES public.usuario(id);


--
-- Name: regra_pontuacao regra_pontuacao_criador_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brasileirao2026
--

ALTER TABLE ONLY public.regra_pontuacao
    ADD CONSTRAINT regra_pontuacao_criador_id_fkey FOREIGN KEY (criador_id) REFERENCES public.usuario(id);


--
-- Name: snapshot_pontuacao snapshot_pontuacao_bolao_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brasileirao2026
--

ALTER TABLE ONLY public.snapshot_pontuacao
    ADD CONSTRAINT snapshot_pontuacao_bolao_id_fkey FOREIGN KEY (bolao_id) REFERENCES public.bolao(id);


--
-- Name: snapshot_pontuacao snapshot_pontuacao_usuario_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brasileirao2026
--

ALTER TABLE ONLY public.snapshot_pontuacao
    ADD CONSTRAINT snapshot_pontuacao_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES public.usuario(id);


--
-- Name: solicitacao_entrada solicitacao_entrada_bolao_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brasileirao2026
--

ALTER TABLE ONLY public.solicitacao_entrada
    ADD CONSTRAINT solicitacao_entrada_bolao_id_fkey FOREIGN KEY (bolao_id) REFERENCES public.bolao(id);


--
-- Name: solicitacao_entrada solicitacao_entrada_respondido_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brasileirao2026
--

ALTER TABLE ONLY public.solicitacao_entrada
    ADD CONSTRAINT solicitacao_entrada_respondido_por_fkey FOREIGN KEY (respondido_por) REFERENCES public.usuario(id);


--
-- Name: solicitacao_entrada solicitacao_entrada_usuario_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brasileirao2026
--

ALTER TABLE ONLY public.solicitacao_entrada
    ADD CONSTRAINT solicitacao_entrada_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES public.usuario(id);


--
-- Name: solicitacao_pagamento solicitacao_pagamento_aprovado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brasileirao2026
--

ALTER TABLE ONLY public.solicitacao_pagamento
    ADD CONSTRAINT solicitacao_pagamento_aprovado_por_fkey FOREIGN KEY (aprovado_por) REFERENCES public.usuario(id);


--
-- Name: solicitacao_pagamento solicitacao_pagamento_bolao_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brasileirao2026
--

ALTER TABLE ONLY public.solicitacao_pagamento
    ADD CONSTRAINT solicitacao_pagamento_bolao_id_fkey FOREIGN KEY (bolao_id) REFERENCES public.bolao(id);


--
-- Name: solicitacao_pagamento solicitacao_pagamento_usuario_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: brasileirao2026
--

ALTER TABLE ONLY public.solicitacao_pagamento
    ADD CONSTRAINT solicitacao_pagamento_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES public.usuario(id);


--
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: -; Owner: postgres
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres GRANT ALL ON SEQUENCES TO brasileirao2026;


--
-- Name: DEFAULT PRIVILEGES FOR TYPES; Type: DEFAULT ACL; Schema: -; Owner: postgres
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres GRANT ALL ON TYPES TO brasileirao2026;


--
-- Name: DEFAULT PRIVILEGES FOR FUNCTIONS; Type: DEFAULT ACL; Schema: -; Owner: postgres
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres GRANT ALL ON FUNCTIONS TO brasileirao2026;


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: -; Owner: postgres
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres GRANT ALL ON TABLES TO brasileirao2026;


--
-- PostgreSQL database dump complete
--

\unrestrict YbeRPjdIiyScvTH828s0dm1RQj6dC6I0zx6ilpFHCrud2gKD9KF4lgagHQrxRKB

