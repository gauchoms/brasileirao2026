import os
import resend

def enviar_email(destinatario, assunto, conteudo_html):
    """
    Envia email via Resend
    """
    try:
        resend.api_key = os.environ.get('RESEND_API_KEY')

        params = {
            "from": os.environ.get('RESEND_FROM_EMAIL', 'Brasileirão 2026 <noreply@brasileirao2026.com>'),
            "to": [destinatario],
            "subject": assunto,
            "html": conteudo_html,
        }

        email = resend.Emails.send(params)
        return True

    except Exception as e:
        print(f"Erro ao enviar email: {str(e)}")
        return False


def email_boas_vindas(usuario):
    """Email de boas-vindas ao cadastrar"""
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h1 style="color: #00a651;">Bem-vindo ao Errei de novo!!! Brinque e palpite nos bolões. Copa do mundo, brasileirão, e muito mais!!!!</h1>
        <p>Olá <strong>{usuario.nome_completo or usuario.username}</strong>,</p>
        <p>Sua conta foi criada com sucesso!</p>
        <p>Agora você pode:</p>
        <ul>
            <li>Criar bolões e desafiar seus amigos</li>
            <li>Fazer palpites e ganhar pontos</li>
            <li>Acompanhar rankings em tempo real</li>
        </ul>
        <p>Acesse: <a href="https://erreidenovo.com.br">erreidenovo.com.br</a></p>
        <p style="color: #666; font-size: 0.9em;">Boa sorte! 🏆</p>
    </div>
    """
    return enviar_email(usuario.email, "Bem-vindo ao Errei de novo! ⚽", html)


def email_solicitacao_entrada(bolao, usuario_solicitante):
    """Email para o dono quando alguém solicita entrar no bolão privado"""
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h1 style="color: #ffd700;">Nova solicitação de entrada!</h1>
        <p>Olá <strong>{bolao.dono.nome_completo or bolao.dono.username}</strong>,</p>
        <p><strong>{usuario_solicitante.nome_completo or usuario_solicitante.username}</strong> quer entrar no seu bolão:</p>
        <h2 style="color: #00a651;">{bolao.nome}</h2>
        <p>Acesse o bolão para aprovar ou rejeitar:</p>
        <a href="https://brasileirao2026.onrender.com/bolao/{bolao.id}" 
           style="display: inline-block; background: #00a651; color: white; padding: 12px 24px; 
                  text-decoration: none; border-radius: 6px; font-weight: bold;">
            Ver Solicitação
        </a>
    </div>
    """
    return enviar_email(bolao.dono.email, f"Nova solicitação - {bolao.nome}", html)


def email_solicitacao_respondida(solicitacao, aprovada):
    """Email para o usuário quando sua solicitação é aprovada/rejeitada"""
    status = "aprovada" if aprovada else "rejeitada"
    cor = "#00a651" if aprovada else "#e74c3c"
    titulo = "Solicitação Aprovada! 🎉" if aprovada else "Solicitação Rejeitada"

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h1 style="color: {cor};">{titulo}</h1>
        <p>Olá <strong>{solicitacao.usuario.nome_completo or solicitacao.usuario.username}</strong>,</p>
        <p>Sua solicitação para entrar no bolão <strong>{solicitacao.bolao.nome}</strong> foi {status}.</p>
    """

    if aprovada:
        html += f"""
        <p>Agora você pode fazer seus palpites!</p>
        <a href="https://erreidenovo.com.br/bolao/{solicitacao.bolao.id}" 
           style="display: inline-block; background: #00a651; color: white; padding: 12px 24px; 
                  text-decoration: none; border-radius: 6px; font-weight: bold;">
            Acessar Bolão
        </a>
        """

    html += "</div>"

    return enviar_email(solicitacao.usuario.email, f"Solicitação {status} - {solicitacao.bolao.nome}", html)


def email_recuperar_senha(usuario, token):
    """Email com link para redefinir senha"""
    base_url = os.environ.get('BASE_URL', 'https://erreidenovo.com.br')
    link = f"{base_url}/redefinir_senha/{token}"

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h1 style="color: #00a651;">Redefinição de Senha</h1>
        <p>Olá <strong>{usuario.nome_completo or usuario.username}</strong>,</p>
        <p>Recebemos uma solicitação para redefinir a senha da sua conta.</p>
        <p>Clique no botão abaixo para criar uma nova senha:</p>
        <a href="{link}"
           style="display: inline-block; background: #00a651; color: white; padding: 12px 24px;
                  text-decoration: none; border-radius: 6px; font-weight: bold; margin: 1rem 0;">
            Redefinir Senha
        </a>
        <p style="color: #666; font-size: 0.9em;">
            Este link é válido por <strong>1 hora</strong>.<br>
            Se você não solicitou isso, ignore este email — sua senha não será alterada.
        </p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 1.5rem 0;">
        <p style="color: #999; font-size: 0.8em;">
            Se o botão não funcionar, copie e cole este link no navegador:<br>
            <a href="{link}" style="color: #00a651;">{link}</a>
        </p>
    </div>
    """
    return enviar_email(usuario.email, "Redefinição de senha - Time Errei de Novo", html)


def email_alerta_palpite(usuario, jogo, bolao, horas_restantes):
    """Alerta para participante que ainda não palpitou em um jogo próximo."""
    if not usuario.email:
        return False

    tc = jogo.time_casa.nome if jogo.time_casa else "?"
    tf = jogo.time_fora.nome if jogo.time_fora else "?"

    from app.utils import converter_utc_brasilia
    data_br = converter_utc_brasilia(jogo.data)
    data_fmt = data_br.strftime("%d/%m/%Y às %H:%M") if data_br else "Em breve"

    if horas_restantes <= 1:
        urgencia = "🚨 ÚLTIMA HORA"
        cor_urgencia = "#e74c3c"
        msg_tempo = "Falta menos de 1 hora!"
    else:
        urgencia = "⏰ LEMBRETE"
        cor_urgencia = "#ff9500"
        msg_tempo = "Faltam aproximadamente 24 horas."

    link_bolao = f"https://erreidenovo.com.br/bolao/{bolao.id}"

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: {cor_urgencia}; padding: 1rem 1.5rem; border-radius: 8px 8px 0 0;">
            <h1 style="color: white; margin: 0; font-size: 1.3rem;">{urgencia} — Você ainda não palpitou!</h1>
        </div>
        <div style="background: #f9f9f9; padding: 1.5rem; border-radius: 0 0 8px 8px; border: 1px solid #eee;">
            <p>Olá <strong>{usuario.nome_completo or usuario.username}</strong>,</p>
            <p>{msg_tempo} O jogo abaixo ainda não tem seu palpite no bolão <strong>{bolao.nome}</strong>:</p>

            <div style="background: #1a3a6e; color: white; padding: 1.2rem; border-radius: 8px;
                        text-align: center; margin: 1.2rem 0;">
                <div style="font-size: 1.3rem; font-weight: 700; margin-bottom: 0.5rem;">
                    {tc} × {tf}
                </div>
                <div style="color: #aac4ff; font-size: 0.9rem;">{data_fmt}</div>
            </div>

            <p style="text-align: center; margin-top: 1.5rem;">
                <a href="{link_bolao}"
                   style="display: inline-block; background: #00a651; color: white;
                          padding: 0.8rem 2rem; border-radius: 6px; text-decoration: none;
                          font-weight: bold; font-size: 1rem;">
                    ⚽ Fazer meu palpite agora
                </a>
            </p>

            <p style="color: #999; font-size: 0.8rem; margin-top: 1.5rem; text-align: center;">
                Após o início do jogo não será mais possível palpitar.<br>
                Para não receber estes alertas, o organizador do bolão pode desativá-los.
            </p>
        </div>
    </div>
    """

    assunto = f"{urgencia} | {tc} × {tf} — {bolao.nome}"
    return enviar_email(usuario.email, assunto, html)
