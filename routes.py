from flask import render_template, request, redirect, url_for, flash
from database.db import get_db_connection

# This file initializes all routes for the GUI.
def init_routes(app):
    # Dashboard
    @app.route('/')
    def index():
        """Dashboard page"""
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Get statistics via stored procedure
        cursor.callproc('sp_get_dashboard_stats')
        stats_row = None
        for result in cursor.stored_results():
            stats_row = result.fetchone()

        cursor.close()
        conn.close()

        if not stats_row:
            stats_row = {
                'total_tournaments': 0,
                'ongoing_tournaments': 0,
                'completed_tournaments': 0
            }

        stats = {
            'total_tournaments': stats_row['total_tournaments'],
            'ongoing_tournaments': stats_row['ongoing_tournaments'],
            'completed_tournaments': stats_row['completed_tournaments']
        }

        return render_template('index.html', stats=stats)

    # Tournaments list
    @app.route('/tournaments')
    def tournaments():
        """List all tournaments"""
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.callproc('sp_get_tournaments')
        tournaments_list = []
        for result in cursor.stored_results():
            tournaments_list = result.fetchall()

        cursor.close()
        conn.close()

        return render_template('tournaments.html', tournaments=tournaments_list)

    # Create tournament
    @app.route('/tournament/create', methods=['GET', 'POST'])
    def create_tournament():
        """Create a new tournament"""
        if request.method == 'POST':
            name = request.form['name']
            start_date = request.form['start_date']
            end_date = request.form['end_date']

            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            try:
                cursor.callproc('sp_create_tournament', [name, start_date, end_date])
                tournament_id = None
                for result in cursor.stored_results():
                    row = result.fetchone()
                    if row:
                        tournament_id = row['tournament_id']

                conn.commit()
                flash('Tournament created successfully!', 'success')
                return redirect(url_for('tournament_detail', tournament_id=tournament_id))
            except Exception as e:
                conn.rollback()
                flash(f'Error creating tournament: {str(e)}', 'danger')
            finally:
                cursor.close()
                conn.close()

        return render_template('create_tournament.html')

    # Tournament detail
    @app.route('/tournament/<int:tournament_id>')
    def tournament_detail(tournament_id):
        """View tournament details with teams, fixtures, and leaderboard"""
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Get tournament info
        cursor.callproc('sp_get_tournament', [tournament_id])
        tournament = None
        for result in cursor.stored_results():
            tournament = result.fetchone()

        if not tournament:
            cursor.close()
            conn.close()
            flash('Tournament not found', 'danger')
            return redirect(url_for('tournaments'))

        # Get teams
        cursor.callproc('sp_get_tournament_teams', [tournament_id])
        teams = []
        for result in cursor.stored_results():
            teams = result.fetchall()

        # Get fixtures
        cursor.callproc('sp_get_tournament_fixtures', [tournament_id])
        fixtures = []
        for result in cursor.stored_results():
            fixtures = result.fetchall()

        # Get leaderboard
        cursor.callproc('sp_get_tournament_leaderboard', [tournament_id])
        leaderboard = []
        for result in cursor.stored_results():
            leaderboard = result.fetchall()

        # Get map pool count
        cursor.callproc('sp_get_tournament_map_pool_count', [tournament_id])
        map_pool_count = 0
        for result in cursor.stored_results():
            row = result.fetchone()
            if row:
                map_pool_count = row['map_pool_count']

        cursor.close()
        conn.close()

        return render_template(
            'tournament_detail.html',
            tournament=tournament,
            teams=teams,
            fixtures=fixtures,
            leaderboard=leaderboard,
            map_pool_count=map_pool_count
        )

    # Add team (with players)
    @app.route('/tournament/<int:tournament_id>/add_team', methods=['GET', 'POST'])
    def add_team(tournament_id):
        """Add a new team with players to a tournament"""
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Get tournament info
        cursor.callproc('sp_get_tournament', [tournament_id])
        tournament = None
        for result in cursor.stored_results():
            tournament = result.fetchone()

        if not tournament:
            cursor.close()
            conn.close()
            flash('Tournament not found', 'danger')
            return redirect(url_for('tournaments'))

        if request.method == 'POST':
            try:
                # Create team
                team_name = request.form['team_name']
                short_name = request.form.get('short_name') or None
                coach_name = request.form['coach_name']
                coach_nickname = request.form.get('coach_nickname') or None

                cursor.callproc(
                    'sp_create_team',
                    [tournament_id, team_name, short_name, coach_name, coach_nickname]
                )
                team_id = None
                for result in cursor.stored_results():
                    row = result.fetchone()
                    if row:
                        team_id = row['team_id']

                # Add 5 starting players
                for i in range(5):
                    player_ign = request.form.get(f'player_ign_{i}')
                    player_real = request.form.get(f'player_real_{i}') or None
                    player_country = request.form.get(f'player_country_{i}') or None

                    if player_ign:
                        cursor.callproc(
                            'sp_create_player',
                            [team_id, player_ign, player_real, player_country, 'PLAYER']
                        )
                        # Consume result
                        for r in cursor.stored_results():
                            r.fetchall()

                # Add substitute if provided
                sub_ign = request.form.get('sub_ign')
                if sub_ign:
                    sub_real = request.form.get('sub_real') or None
                    sub_country = request.form.get('sub_country') or None

                    cursor.callproc(
                        'sp_create_player',
                        [team_id, sub_ign, sub_real, sub_country, 'SUBSTITUTE']
                    )
                    for r in cursor.stored_results():
                        r.fetchall()

                conn.commit()
                flash(f'Team "{team_name}" added successfully!', 'success')
                return redirect(url_for('tournament_detail', tournament_id=tournament_id))

            except Exception as e:
                conn.rollback()
                flash(f'Error adding team: {str(e)}', 'danger')

        cursor.close()
        conn.close()

        return render_template('add_team.html', tournament=tournament)

    # Start tournament (generate fixtures)
    @app.route('/tournament/<int:tournament_id>/start', methods=['POST'])
    def start_tournament(tournament_id):
        """Start tournament and generate fixtures"""
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.callproc('sp_start_tournament', [tournament_id])
            conn.commit()
            flash('Tournament started and fixtures generated!', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'Error starting tournament: {str(e)}', 'danger')
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('tournament_detail', tournament_id=tournament_id))

    # Setup map pool
    @app.route('/tournament/<int:tournament_id>/map_pool', methods=['GET', 'POST'])
    def setup_map_pool(tournament_id):
        """Setup map pool for tournament"""
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Get tournament
        cursor.callproc('sp_get_tournament', [tournament_id])
        tournament = None
        for result in cursor.stored_results():
            tournament = result.fetchone()

        if not tournament:
            cursor.close()
            conn.close()
            flash('Tournament not found', 'danger')
            return redirect(url_for('tournaments'))

        # Get all active maps
        cursor.callproc('sp_get_active_maps')
        all_maps = []
        for result in cursor.stored_results():
            all_maps = result.fetchall()

        # Get current map pool
        cursor.callproc('sp_get_tournament_map_pool', [tournament_id])
        selected_maps = []
        for result in cursor.stored_results():
            selected_maps = result.fetchall()
        selected_map_ids = [m['map_id'] for m in selected_maps]

        if request.method == 'POST':
            try:
                # Clear existing map pool via procedure
                cursor.callproc('sp_clear_tournament_map_pool', [tournament_id])
                for r in cursor.stored_results():
                    r.fetchall()

                # Add selected maps
                map_ids = request.form.getlist('map_ids')
                for map_id in map_ids:
                    cursor.callproc('sp_add_map_to_tournament_pool',
                                    [tournament_id, int(map_id)])
                    for r in cursor.stored_results():
                        r.fetchall()

                conn.commit()
                flash('Map pool updated successfully!', 'success')
                return redirect(url_for('tournament_detail', tournament_id=tournament_id))

            except Exception as e:
                conn.rollback()
                flash(f'Error updating map pool: {str(e)}', 'danger')

        cursor.close()
        conn.close()

        return render_template(
            'setup_map_pool.html',
            tournament=tournament,
            all_maps=all_maps,
            selected_map_ids=selected_map_ids
        )


    # Team detail
    @app.route('/team/<int:team_id>')
    def team_detail(team_id):
        """View team details and players"""
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Get team info via proc
        cursor.callproc('sp_get_team', [team_id])
        team = None
        for result in cursor.stored_results():
            team = result.fetchone()

        if not team:
            cursor.close()
            conn.close()
            flash('Team not found', 'danger')
            return redirect(url_for('tournaments'))

        # Get players
        cursor.callproc('sp_get_team_players', [team_id])
        players = []
        for result in cursor.stored_results():
            players = result.fetchall()

        cursor.close()
        conn.close()

        return render_template('team_detail.html', team=team, players=players)

    # Manage fixture (view + forms)
    @app.route('/fixture/<int:fixture_id>')
    def manage_fixture(fixture_id):
        """Manage fixture phases and record results"""
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Get fixture details (with team names, map name, tournament_id)
        cursor.callproc('sp_get_fixture_detail', [fixture_id])
        fixture = None
        for result in cursor.stored_results():
            fixture = result.fetchone()

        if not fixture:
            cursor.close()
            conn.close()
            flash('Fixture not found', 'danger')
            return redirect(url_for('tournaments'))

        # Get available maps from tournament pool
        cursor.callproc('sp_get_maps_for_tournament_pool', [fixture['tournament_id']])
        maps = []
        for result in cursor.stored_results():
            maps = result.fetchall()

        # Get officials
        cursor.callproc('sp_get_officials')
        officials = []
        for result in cursor.stored_results():
            officials = result.fetchall()

        # Get servers
        cursor.callproc('sp_get_servers')
        servers = []
        for result in cursor.stored_results():
            servers = result.fetchall()

        # Get players for both teams (only starting players)
        cursor.callproc('sp_get_team_players_by_role', [fixture['home_team_id'], 'PLAYER'])
        home_players = []
        for result in cursor.stored_results():
            home_players = result.fetchall()

        cursor.callproc('sp_get_team_players_by_role', [fixture['away_team_id'], 'PLAYER'])
        away_players = []
        for result in cursor.stored_results():
            away_players = result.fetchall()

        # If fixture is ended, get player stats
        player_stats = []
        if fixture['phase'] == 'END':
            cursor.callproc('sp_get_fixture_stats', [fixture_id])
            for result in cursor.stored_results():
                stats = result.fetchall()
                # Add team names to stats
                for stat in stats:
                    if stat['team_id'] == fixture['home_team_id']:
                        stat['team_name'] = fixture['home_team_name']
                    else:
                        stat['team_name'] = fixture['away_team_name']
                player_stats = stats

        cursor.close()
        conn.close()

        return render_template(
            'manage_fixture.html',
            fixture=fixture,
            maps=maps,
            officials=officials,
            servers=servers,
            home_players=home_players,
            away_players=away_players,
            player_stats=player_stats
        )

    # Fixture phases: Map selection
    @app.route('/fixture/<int:fixture_id>/map_selection', methods=['POST'])
    def set_map_selection(fixture_id):
        """Set map, official, server and move to MAP_SELECTION phase"""
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            map_id = request.form['map_id']
            official_id = request.form['official_id']
            server_id = request.form['server_id']

            cursor.callproc(
                'sp_set_fixture_map_selection',
                [fixture_id, map_id, official_id, server_id]
            )
            conn.commit()
            flash('Match started - Map selection complete!', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'Error: {str(e)}', 'danger')
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('manage_fixture', fixture_id=fixture_id))

    # Fixture edit (meta-data)
    @app.route('/fixture/<int:fixture_id>/edit', methods=['POST'])
    def edit_fixture(fixture_id):
        """
        Edit fixture meta-data:
        - phase
        - scheduled date & time
        - map, official, server
        """
        phase = request.form.get('phase')

        scheduled_date = request.form.get('scheduled_date')
        scheduled_time = request.form.get('scheduled_time')
        if scheduled_date and scheduled_time:
            scheduled_at = f"{scheduled_date} {scheduled_time}:00"
        else:
            scheduled_at = None

        map_id = request.form.get('map_id') or None
        official_id = request.form.get('official_id') or None
        server_id = request.form.get('server_id') or None

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.callproc(
                'sp_update_fixture',
                [fixture_id, phase, scheduled_at, map_id, official_id, server_id]
            )
            for result in cursor.stored_results():
                result.fetchall()

            conn.commit()
            flash('Fixture updated successfully!', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'Error updating fixture: {str(e)}', 'danger')
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('manage_fixture', fixture_id=fixture_id))

    # Fixture phases: In progress
    @app.route('/fixture/<int:fixture_id>/in_progress', methods=['POST'])
    def set_in_progress(fixture_id):
        """Move fixture to IN_PROGRESS phase"""
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.callproc('sp_set_fixture_in_progress', [fixture_id])
            conn.commit()
            flash('Match is now in progress!', 'info')
        except Exception as e:
            conn.rollback()
            flash(f'Error: {str(e)}', 'danger')
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('manage_fixture', fixture_id=fixture_id))

    # Fixture phases: End match
    @app.route('/fixture/<int:fixture_id>/end', methods=['POST'])
    def end_fixture(fixture_id):
        """End fixture and record all stats"""
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            home_score = request.form['home_score']
            away_score = request.form['away_score']

            # End the fixture (this updates scores, winner, and leaderboard)
            cursor.callproc('sp_end_fixture', [fixture_id, home_score, away_score])

            # Now insert player stats
            for key, value in request.form.items():
                if key.startswith('player_') and key.endswith('_kills'):
                    player_id = key.split('_')[1]
                    kills = int(request.form.get(f'player_{player_id}_kills', 0))
                    deaths = int(request.form.get(f'player_{player_id}_deaths', 0))
                    assists = int(request.form.get(f'player_{player_id}_assists', 0))

                    cursor.callproc(
                        'sp_upsert_fixture_player_stats',
                        [fixture_id, player_id, kills, deaths, assists]
                    )

            conn.commit()
            flash('Match completed and stats recorded!', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'Error ending match: {str(e)}', 'danger')
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('manage_fixture', fixture_id=fixture_id))

    # Manage data (maps, officials, servers)
    @app.route('/manage-data')
    def manage_data():
        """Manage maps, officials, and servers"""
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Get all maps
        cursor.callproc('sp_get_maps')
        maps = []
        for result in cursor.stored_results():
            maps = result.fetchall()

        # Get all officials
        cursor.callproc('sp_get_officials')
        officials = []
        for result in cursor.stored_results():
            officials = result.fetchall()

        # Get all servers
        cursor.callproc('sp_get_servers')
        servers = []
        for result in cursor.stored_results():
            servers = result.fetchall()

        cursor.close()
        conn.close()

        return render_template(
            'manage_data.html',
            maps=maps,
            officials=officials,
            servers=servers
        )

    @app.route('/add-map', methods=['POST'])
    def add_map():
        """Add a new map"""
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            map_name = request.form['map_name']
            map_code = request.form['map_code']

            cursor.callproc('sp_create_map', [map_name, map_code])
            for result in cursor.stored_results():
                result.fetchall()

            conn.commit()
            flash(f'Map "{map_name}" added successfully!', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'Error adding map: {str(e)}', 'danger')
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('manage_data'))

    @app.route('/add-official', methods=['POST'])
    def add_official():
        """Add a new official"""
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            official_name = request.form['official_name']

            cursor.callproc('sp_create_official', [official_name])
            for result in cursor.stored_results():
                result.fetchall()

            conn.commit()
            flash(f'Official "{official_name}" added successfully!', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'Error adding official: {str(e)}', 'danger')
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('manage_data'))

    @app.route('/add-server', methods=['POST'])
    def add_server():
        """Add a new server"""
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            server_name = request.form['server_name']
            server_location = request.form.get('server_location') or None
            server_ip = request.form.get('server_ip') or None

            cursor.callproc('sp_create_server', [server_name, server_location, server_ip])
            for result in cursor.stored_results():
                result.fetchall()

            conn.commit()
            flash(f'Server "{server_name}" added successfully!', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'Error adding server: {str(e)}', 'danger')
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('manage_data'))

    @app.route('/map/<int:map_id>/edit', methods=['POST'])
    def edit_map(map_id):
        """Edit an existing map"""
        map_name = request.form['map_name']
        map_code = request.form['map_code']
        is_active = request.form.get('is_active', '0')  # checkbox
        is_active_bool = 1 if is_active == '1' else 0

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.callproc('sp_update_map', [map_id, map_name, map_code, is_active_bool])
            for result in cursor.stored_results():
                result.fetchall()

            conn.commit()
            flash('Map updated successfully!', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'Error updating map: {str(e)}', 'danger')
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('manage_data'))

    @app.route('/official/<int:official_id>/edit', methods=['POST'])
    def edit_official(official_id):
        """Edit an existing official"""
        official_name = request.form['official_name']

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.callproc('sp_update_official', [official_id, official_name])
            for result in cursor.stored_results():
                result.fetchall()

            conn.commit()
            flash('Official updated successfully!', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'Error updating official: {str(e)}', 'danger')
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('manage_data'))

    @app.route('/server/<int:server_id>/edit', methods=['POST'])
    def edit_server(server_id):
        """Edit an existing server"""
        server_name = request.form['server_name']
        server_location = request.form.get('server_location') or None
        server_ip = request.form.get('server_ip') or None

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.callproc(
                'sp_update_server',
                [server_id, server_name, server_location, server_ip]
            )
            for result in cursor.stored_results():
                result.fetchall()

            conn.commit()
            flash('Server updated successfully!', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'Error updating server: {str(e)}', 'danger')
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('manage_data'))

    # Edit tournament
    @app.route('/tournament/<int:tournament_id>/edit', methods=['GET', 'POST'])
    def edit_tournament(tournament_id):
        """Edit tournament information"""
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Get tournament info
        cursor.callproc('sp_get_tournament', [tournament_id])
        tournament = None
        for result in cursor.stored_results():
            tournament = result.fetchone()

        if not tournament:
            cursor.close()
            conn.close()
            flash('Tournament not found', 'danger')
            return redirect(url_for('tournaments'))

        if request.method == 'POST':
            try:
                name = request.form['name']
                start_date = request.form['start_date']
                end_date = request.form['end_date']
                status = request.form['status']

                cursor = conn.cursor()
                cursor.callproc(
                    'sp_update_tournament',
                    [tournament_id, name, start_date, end_date, status]
                )
                for result in cursor.stored_results():
                    result.fetchall()

                conn.commit()
                flash('Tournament updated successfully!', 'success')
                cursor.close()
                conn.close()
                return redirect(url_for('tournament_detail', tournament_id=tournament_id))

            except Exception as e:
                conn.rollback()
                flash(f'Error updating tournament: {str(e)}', 'danger')

        cursor.close()
        conn.close()

        return render_template('edit_tournament.html', tournament=tournament)

    # Edit team (and players)
    @app.route('/team/<int:team_id>/edit', methods=['GET', 'POST'])
    def edit_team(team_id):
        """Edit team and player information"""
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Get team info
        cursor.callproc('sp_get_team', [team_id])
        team = None
        for result in cursor.stored_results():
            team = result.fetchone()

        if not team:
            cursor.close()
            conn.close()
            flash('Team not found', 'danger')
            return redirect(url_for('tournaments'))

        # Get players
        cursor.callproc('sp_get_team_players', [team_id])
        players = []
        for result in cursor.stored_results():
            players = result.fetchall()

        if request.method == 'POST':
            try:
                # Update team info
                team_name = request.form['team_name']
                short_name = request.form.get('short_name') or None
                coach_name = request.form['coach_name']
                coach_nickname = request.form.get('coach_nickname') or None

                cursor2 = conn.cursor()
                cursor2.callproc(
                    'sp_update_team',
                    [team_id, team_name, short_name, coach_name, coach_nickname]
                )
                for r in cursor2.stored_results():
                    r.fetchall()

                # Update players
                player_count = int(request.form['player_count'])
                for i in range(player_count):
                    player_id = request.form.get(f'player_id_{i}')
                    player_ign = request.form.get(f'player_ign_{i}')
                    player_real = request.form.get(f'player_real_{i}') or None
                    player_country = request.form.get(f'player_country_{i}') or None

                    if player_id and player_ign:
                        cursor2.callproc(
                            'sp_update_player',
                            [int(player_id), player_ign, player_real, player_country]
                        )
                        for r in cursor2.stored_results():
                            r.fetchall()

                conn.commit()
                cursor2.close()
                flash('Team updated successfully!', 'success')
                return redirect(url_for('tournament_detail', tournament_id=team['tournament_id']))

            except Exception as e:
                conn.rollback()
                flash(f'Error updating team: {str(e)}', 'danger')

        cursor.close()
        conn.close()

        return render_template('edit_team.html', team=team, players=players)

    # View all data (admin overview)
    @app.route('/view-all-data')
    def view_all_data():
        """View all system data"""
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Get all tournaments with team counts
        cursor.callproc('sp_get_all_tournaments_summary')
        tournaments = []
        for result in cursor.stored_results():
            tournaments = result.fetchall()

        # Get all teams with player counts and tournament names
        cursor.callproc('sp_get_all_teams_summary')
        teams = []
        for result in cursor.stored_results():
            teams = result.fetchall()

        # Get all players with team and tournament names
        cursor.callproc('sp_get_all_players_summary')
        players = []
        for result in cursor.stored_results():
            players = result.fetchall()

        # Get all fixtures with details
        cursor.callproc('sp_get_all_fixtures_summary')
        fixtures = []
        for result in cursor.stored_results():
            fixtures = result.fetchall()

        # Get all maps
        cursor.callproc('sp_get_maps')
        maps = []
        for result in cursor.stored_results():
            maps = result.fetchall()

        # Get all officials
        cursor.callproc('sp_get_officials')
        officials = []
        for result in cursor.stored_results():
            officials = result.fetchall()

        # Get all servers
        cursor.callproc('sp_get_servers')
        servers = []
        for result in cursor.stored_results():
            servers = result.fetchall()

        cursor.close()
        conn.close()

        return render_template(
            'view_all_data.html',
            tournaments=tournaments,
            teams=teams,
            players=players,
            fixtures=fixtures,
            maps=maps,
            officials=officials,
            servers=servers
        )

    # Tournament Winner Management
    @app.route('/tournament/<int:tournament_id>/winner', methods=['GET', 'POST'])
    def manage_tournament_winner(tournament_id):
        """Manage tournament winner - show tied teams or winner"""
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.callproc('sp_get_tournament', [tournament_id])
        tournament = None
        for result in cursor.stored_results():
            tournament = result.fetchone()

        if not tournament:
            cursor.close()
            conn.close()
            flash('Tournament not found', 'danger')
            return redirect(url_for('tournaments'))

        if tournament['status'] != 'COMPLETED':
            cursor.close()
            conn.close()
            flash('Tournament is not yet completed', 'warning')
            return redirect(url_for('tournament_detail', tournament_id=tournament_id))

        cursor.callproc('sp_get_tied_teams_for_winner', [tournament_id])
        tied_teams = []
        for result in cursor.stored_results():
            tied_teams = result.fetchall()

        if request.method == 'POST':
            winner_team_id = request.form.get('winner_team_id')

            if not winner_team_id:
                flash('Please select a winner team', 'danger')
            else:
                try:
                    cursor2 = conn.cursor()
                    cursor2.callproc('sp_set_tournament_winner_manual',
                                     [tournament_id, int(winner_team_id)])
                    for r in cursor2.stored_results():
                        r.fetchall()

                    conn.commit()
                    cursor2.close()
                    flash('Tournament winner set successfully!', 'success')

                    cursor.close()
                    conn.close()
                    return redirect(url_for('tournament_detail', tournament_id=tournament_id))

                except Exception as e:
                    conn.rollback()
                    flash(f'Error setting winner: {str(e)}', 'danger')

        cursor.close()
        conn.close()

        return render_template(
            'manage_winner.html',
            tournament=tournament,
            tied_teams=tied_teams
        )

    @app.route('/tournament/<int:tournament_id>/recalculate_winner', methods=['POST'])
    def recalculate_winner(tournament_id):
        """Recalculate tournament winner (admin action)"""
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.callproc('sp_determine_tournament_winner_with_result', [tournament_id])

            result_data = None
            for result in cursor.stored_results():
                result_data = result.fetchone()

            conn.commit()

            if result_data:
                if result_data['decided_by'] == 'MANUAL':
                    flash(f"Tournament has {result_data['tied_teams_count']} teams tied. Manual winner selection required.", 'warning')
                    cursor.close()
                    conn.close()
                    return redirect(url_for('manage_tournament_winner', tournament_id=tournament_id))
                else:
                    flash(f"Winner determined by {result_data['decided_by']}!", 'success')
            else:
                flash('Winner calculation completed', 'info')

        except Exception as e:
            conn.rollback()
            flash(f'Error recalculating winner: {str(e)}', 'danger')
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('tournament_detail', tournament_id=tournament_id))

    @app.route('/tournament/<int:tournament_id>/clear_winner', methods=['POST'])
    def clear_winner(tournament_id):
        """Clear tournament winner (admin action)"""
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.callproc('sp_clear_tournament_winner', [tournament_id])
            for r in cursor.stored_results():
                r.fetchall()

            conn.commit()
            flash('Tournament winner cleared successfully!', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'Error clearing winner: {str(e)}', 'danger')
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('tournament_detail', tournament_id=tournament_id))

    @app.route('/tournament/<int:tournament_id>/delete', methods=['POST'])
    def delete_tournament(tournament_id):
        """
        Delete a tournament.
        This cascades to teams, fixtures, leaderboard, etc. via FKs.
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.callproc('sp_delete_tournament', [tournament_id])
            for result in cursor.stored_results():
                result.fetchall()

            conn.commit()
            flash('Tournament deleted successfully!', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'Error deleting tournament: {str(e)}', 'danger')
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('tournaments'))

    # Delete team
    @app.route('/team/<int:team_id>/delete', methods=['POST'])
    def delete_team(team_id):
        """
        Delete a team (only allowed if no fixtures exist for this team;
        enforced in sp_delete_team).
        """
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.callproc('sp_get_team', [team_id])
            team = None
            for result in cursor.stored_results():
                team = result.fetchone()

            if not team:
                flash('Team not found.', 'danger')
                return redirect(url_for('tournaments'))

            tournament_id = team['tournament_id']
            cursor2 = conn.cursor()
            cursor2.callproc('sp_delete_team', [team_id])
            for r in cursor2.stored_results():
                r.fetchall()

            conn.commit()
            flash(f'Team "{team["name"]}" deleted successfully!', 'success')
            return redirect(url_for('tournament_detail', tournament_id=tournament_id))
        except Exception as e:
            conn.rollback()
            flash(f'Error deleting team: {str(e)}', 'danger')
            return redirect(url_for('tournaments'))
        finally:
            cursor.close()
            conn.close()

    # Delete player
    @app.route('/team/<int:team_id>/player/<int:player_id>/delete', methods=['POST'])
    def delete_player(team_id, player_id):
        """
        Delete a player from the system.
        Stats are removed via ON DELETE CASCADE from fixture_player_stats.
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.callproc('sp_delete_player', [player_id])
            for result in cursor.stored_results():
                result.fetchall()

            conn.commit()
            flash('Player deleted successfully!', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'Error deleting player: {str(e)}', 'danger')
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('team_detail', team_id=team_id))

    # Delete map
    @app.route('/map/<int:map_id>/delete', methods=['POST'])
    def delete_map(map_id):
        """Delete a map (automatically removed from any tournament pools)."""
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.callproc('sp_delete_map', [map_id])
            for result in cursor.stored_results():
                result.fetchall()

            conn.commit()
            flash('Map deleted successfully!', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'Error deleting map: {str(e)}', 'danger')
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('manage_data'))

    # Delete official
    @app.route('/official/<int:official_id>/delete', methods=['POST'])
    def delete_official(official_id):
        """Delete an official (unassigned from fixtures first)."""
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.callproc('sp_delete_official', [official_id])
            for result in cursor.stored_results():
                result.fetchall()

            conn.commit()
            flash('Official deleted successfully!', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'Error deleting official: {str(e)}', 'danger')
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('manage_data'))

    # Delete server
    @app.route('/server/<int:server_id>/delete', methods=['POST'])
    def delete_server(server_id):
        """Delete a server (unassigned from fixtures first)."""
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.callproc('sp_delete_server', [server_id])
            for result in cursor.stored_results():
                result.fetchall()

            conn.commit()
            flash('Server deleted successfully!', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'Error deleting server: {str(e)}', 'danger')
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('manage_data'))

    # Delete fixture
    @app.route('/fixture/<int:fixture_id>/delete', methods=['POST'])
    def delete_fixture(fixture_id):
        """
        Delete a single fixture and rebuild leaderboard for its tournament.
        tournament_id is sent from the form for redirect.
        """
        tournament_id = request.form.get('tournament_id', type=int)

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.callproc('sp_delete_fixture', [fixture_id])
            for result in cursor.stored_results():
                result.fetchall()

            conn.commit()
            flash('Fixture deleted successfully!', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'Error deleting fixture: {str(e)}', 'danger')
        finally:
            cursor.close()
            conn.close()

        if tournament_id:
            return redirect(url_for('tournament_detail', tournament_id=tournament_id))
        return redirect(url_for('tournaments'))
