from app import create_app, db
from app.models import Time, Jogo
from app.api import get_jogos_brasileirao, processar_jogos

app = create_app()

with app.app_context():
    db.create_all()

    print("Buscando jogos na API...")
    data = get_jogos_brasileirao()
    jogos = processar_jogos(data)
    print(f"{len(jogos)} jogos encontrados.")

    times_cadastrados = {}

    for jogo in jogos:
        # Cadastra time da casa se ainda não existe
        if jogo['time_casa_id'] not in times_cadastrados:
            time = Time.query.filter_by(api_id=jogo['time_casa_id']).first()
            if not time:
                time = Time(api_id=jogo['time_casa_id'], nome=jogo['time_casa'])
                db.session.add(time)
                db.session.flush()
            times_cadastrados[jogo['time_casa_id']] = time.id

        # Cadastra time de fora se ainda não existe
        if jogo['time_fora_id'] not in times_cadastrados:
            time = Time.query.filter_by(api_id=jogo['time_fora_id']).first()
            if not time:
                time = Time(api_id=jogo['time_fora_id'], nome=jogo['time_fora'])
                db.session.add(time)
                db.session.flush()
            times_cadastrados[jogo['time_fora_id']] = time.id

        # Cadastra jogo se ainda não existe
        jogo_existente = Jogo.query.filter_by(api_id=jogo['api_id']).first()
        if not jogo_existente:
            novo_jogo = Jogo(
                api_id=jogo['api_id'],
                rodada=jogo['rodada'],
                time_casa_id=times_cadastrados[jogo['time_casa_id']],
                time_fora_id=times_cadastrados[jogo['time_fora_id']],
                data=jogo['data'],
                gols_casa=jogo['gols_casa'],
                gols_fora=jogo['gols_fora']
            )
            db.session.add(novo_jogo)

    db.session.commit()
    print("Jogos importados com sucesso!")

    # Lista os times cadastrados
    times = Time.query.all()
    print(f"\n{len(times)} times cadastrados:")
    for time in times:
        print(f"  - {time.nome}")