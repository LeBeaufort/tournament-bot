import nextcord
from nextcord.ext import commands
import sqlite3
from json import dumps, loads

# creating a database connection
db = sqlite3.connect(database="database.db")
con = db.cursor()

#  get the token from the config file
bot_token = open('token.txt', 'r').read()

# creating the bot
bot = commands.Bot(intents=nextcord.Intents.all())

#  loading the json file
json_file = open("setting.json", "r")
bot_settings = loads(json_file.read())


#  some functions here

def is_player_in_a_team(player_name):
    """the function check if the player is already in a team"""
    result = []
    requests = [f'SELECT id FROM teams WHERE p1= "{player_name}"',
                f'SELECT id FROM teams WHERE p2= "{player_name}"']
    for request in requests:
        con.execute(request)
        sql_result = con.fetchall()
        if sql_result:  # Check if the list isn't empty
            return True
        return False


def db_create_team(team_name, p1, p2):
    request = f'INSERT INTO teams (p1, p2, name) VALUES ("{p1}", "{p2}", "{team_name}");'
    try:
        con.execute(request)
        con.fetchall()
        db.commit()
        return True
    except sqlite3.OperationalError:
        return False


def sort_by_point():
    output = {}
    #  in first get all teams in a python dict
    con.execute('Select id from teams')
    teams_id = con.fetchall()
    #  then get info about the team
    template_request = {"points": 'SELECT SUM(point_number) FROM `points` WHERE team_id={}',
                        "p1": 'SELECT p1 FROM teams WHERE id = "{}"',
                        "p2": 'SELECT p2 FROM teams WHERE id = "{}"'}
    for team_id in teams_id:
        short_output = {}
        for request in template_request:
            con.execute(template_request[request].format(team_id[0]))
            result = con.fetchall()[0][0]
            short_output[request] = result
        con.execute(f'SELECT name FROM teams WHERE id="{team_id[0]}"')
        output[con.fetchall()[0][0]] = short_output

    #  output = {key: val for key, val in sorted(output.items(), key=lambda ele: ele[1], reverse=True)}
    return output


def get_team_id_from_name(player_name):
    requests = [f'Select id from teams where p1= "{player_name}"', f'Select id from teams where p2= "{player_name}"']
    for request in requests:
        con.execute(request)
        r = con.fetchall()
        if len(r) != 0:
            return r[0][0]
    return None


def sql_add_points(team_id, game, point_number):
    request = f'INSERT INTO points (team_id, jeu, point_number) VALUES ({team_id}, "{game}", {point_number})'
    con.execute(request)
    db.commit()


def team_name_from_player_name(player_name):
    requests = [f'SELECT name FROM teams WHERE p1="{player_name}"', f'SELECT name FROM teams WHERE p2="{player_name}"']
    for request in requests:
        con.execute(request)
        r = con.fetchall()
        if len(r) != 0:
            return r[0][0]
    return None


def create_leaderboard_table(data):
    leaderboard_list = []
    #  sort the data
    sorted_data = sorted(data.items(), key=lambda x: x[1]['points'], reverse=True)

    # create a dict that contains the top of the leaderboard + sorted_data
    top = {"top_leaderboard": {'points': "points", 'p1': 'Joueur 1 ', 'p2': 'Joueur 2'}}
    top.update(sorted_data)

    #  find the longest in each category
    max_name_length = max(len(name) for name in top.keys())
    max_points_length = max(len(str(value['points'])) for _, value in top.items())
    max_p1_length = max(len(str(value['p1'])) for _, value in top.items())
    max_p2_length = max(len(str(value['p2'])) for _, value in top.items())

    # define an objective to reach in every category
    name_objective = max_name_length + 5
    point_objective = max_points_length + 5
    p1_objective = max_p1_length + 5
    p2_objective = max_p2_length + 5

    #  now create the leaderboard
    for team in top:
        line_template = "|{}{}|{}{}|{}{}|{}{}|"
        current_points = top[team]['points']
        current_name = team
        current_p1 = top[team]['p1']
        current_p2 = top[team]['p2']

        #  now format the default line
        line = line_template.format(
            current_name, " " * (name_objective - len(str(current_name))),
            current_points, " " * (point_objective - len(str(current_points))),
            current_p1, " " * (p1_objective - len(str(current_p1))),
            current_p2, " " * (p2_objective - len(str(current_p2)))
        )

        #  save the line in the list output
        leaderboard_list.append(line)
        leaderboard_list.append(line_template.format(
            "-" * name_objective, "",
            "-" * point_objective, "",
            "-" * p1_objective, "",
            "-" * p2_objective, "",
        ))

    # at the end, return the leaderboard list
    return leaderboard_list


#  ===============================================================


@bot.event
async def on_ready():
    print('The bot is connected !')


@bot.slash_command(name="ping", description="vérifier si le bot est en ligne")
async def ping(interaction: nextcord.Interaction):
    await interaction.send('Pong ! Le bot est en ligne')


@bot.slash_command(name="creer-une-equipe", description="cette commande crée une équipe")
async def create_team(interaction: nextcord.Interaction, nom_d_equip: str, équipier: nextcord.User): # ici

    #  in first check if you can create a team
    inscription_status = loads(open("inscription.json", 'r').read())["inscription"]
    if not inscription_status:
        await interaction.send('Les inscriptions sont fermées, vous ne pouvez pas créer d\'équipe')
        return
    # in first check if settings are correct
    if interaction.user.name == équipier.name or équipier.bot:
        # if the user try to play with a bot or select himself as teammate
        await interaction.send('Tu ne peux pas jouer seul !')
        return
    #  in second check if the two players can join a team
    if is_player_in_a_team(interaction.user.name):
        await interaction.send('Vous êtes déjà dans une équipe !')

    elif is_player_in_a_team(équipier.name):
        await interaction.send(f'Le joueur {équipier.name}, est déjà dans une équipe')

    else:
        #  creating the team, if the players can join
        result = db_create_team(team_name=nom_d_equip, p1=interaction.user.name, p2=équipier)
        if result:
            #  get the role and add it to the two members
            team_role = interaction.guild.get_role(bot_settings["is_in_team_role_id"])
            await interaction.user.add_roles(team_role)
            await équipier.add_roles(team_role)

            await interaction.send(f'Vous êtes désormais dans l\'équipe {nom_d_equip} !')
        else:
            await interaction.send('Umm, il semble qu\' il y ai eu une erreur pendant la création de votre équipe !')


@bot.slash_command(name="liste-equipes",
                   description="cette commande affiche la liste des équipes inscrites et le nombre de point.")
async def team_info(interaction: nextcord.Interaction):
    #  sort the teams by point
    datas = sort_by_point()
    list_learder_board = create_leaderboard_table(data=datas)
    text_leader_board = "Voici le leaderboard ! \n ```"
    for line in list_learder_board:
        text_leader_board += line + "\n"

    text_leader_board += "```"
    await interaction.send(text_leader_board)


@bot.slash_command(name="ajouter-des-points",
                   description="cette commande ajoute des points a une équipe. réservé aux modérateur")
async def add_points(interaction: nextcord.Interaction, equipe_de: nextcord.User, jeu: str, points: int):
    have_the_role = False
    for role in interaction.user.roles:  # check if the user have the role
        if role.name == bot_settings['name_authorised_role']:
            have_the_role = True

    if have_the_role:
        #  in first get the id of the team
        team_id = get_team_id_from_name(equipe_de.name)
        if team_id is not None:
            sql_add_points(team_id=team_id,
                           game=jeu,
                           point_number=points)
            await interaction.send(
                f"Fait ! {points} ont été ajoutés à l'équipe {team_name_from_player_name(equipe_de.name)}, l'équipe de {equipe_de.mention}")
    else:
        await interaction.send("Vous n'avez pas le droit de faire ceci !")


@bot.slash_command(name="inscription",
                   description="cette commande ferme ou ouvre les inscription. réserver aux modérateurs")
async def set_inscription(interaction: nextcord.Interaction, inscription: bool = nextcord.SlashOption(
    name="status",
    choices={True: "Ouvertes", False: "Fermés"}
)):
    has_role = False
    for role in interaction.user.roles:
        if role.name == bot_settings['name_authorised_role']:
            has_role = True
            break
    if has_role:
        json_status = dumps({"inscription": inscription})
        open('inscription.json', 'w').write(json_status)
        equi = {False: "Fermées", True: "Ouvertes"}
        await interaction.send(f'Les inscription sont maintenant {equi[inscription]}')
    else:
        await interaction.send("Vous ne pouvez pas effectuer cette action !")


#  run the bot
if __name__ == "__main__":
    bot.run(bot_token)
