# RushB — CS:GO Tournament Management System

A full-stack web application for managing CS:GO esports tournaments, built with Flask and MySQL. Create tournaments, register teams with rosters, generate round-robin fixtures, track match results with player stats, and determine winners through an automated leaderboard system.

## Features

- **Tournament Management** — Create, edit, start, and complete tournaments with date tracking and status management
- **Team & Roster Management** — Register teams with coaches, 5 starting players, and an optional substitute, each with IGN, real name, and country
- **Round-Robin Fixture Generation** — Automatically generates all matchups when a tournament is started
- **Match Lifecycle** — Fixtures progress through phases: Scheduled → Map Selection → In Progress → End, with map/server/official assignment
- **Player Statistics** — Record kills, deaths, and assists per player per match
- **Leaderboard & Winner Determination** — Automatic standings calculation with tiebreaker logic; manual override for unresolvable ties
- **Map Pool Configuration** — Configure which maps are available per tournament from a global map registry
- **Data Management** — Admin views for managing maps, officials, servers, and a full data overview

## Tech Stack

- **Backend:** Python, Flask
- **Database:** MySQL (all business logic in stored procedures)
- **Frontend:** Jinja2 templates, Bootstrap 5, Bootstrap Icons

## Prerequisites

- Python 3.8+
- MySQL 8.0+
- A MySQL database with the required schema and stored procedures (see [Database Setup](#database-setup))

## Getting Started

1. **Clone the repository**
   ```bash
   git clone https://github.com/prateekdas7/rushB.git
   cd rushB
   ```

2. **Create a virtual environment and install dependencies**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Set up the database**

   Create a MySQL database named `rushb` (or your preferred name) and run the SQL schema script to create all tables and stored procedures. The application relies on stored procedures for all database operations — see [Database Setup](#database-setup) for details.

4. **Run the application**
   ```bash
   python app.py
   ```
   You'll be prompted to enter your MySQL connection credentials. Once connected, the app will be available at `http://localhost:5000`.

## Database Setup

The application delegates all data operations to MySQL stored procedures (prefixed with `sp_`). You'll need to run the schema SQL against your database before starting the app. The schema includes:

- **Tables:** tournaments, teams, players, fixtures, leaderboard, maps, tournament_map_pool, officials, servers, fixture_player_stats
- **Stored Procedures:** ~30 procedures handling CRUD, fixture generation, leaderboard updates, winner determination, and more

> If you have the SQL dump, run it with: `mysql -u <user> -p rushb < schema.sql`

## Project Structure

```
rushB/
├── app.py              # Application entry point & DB credential prompt
├── config.py           # Flask & database configuration
├── routes.py           # All Flask route handlers
├── requirements.txt
├── database/
│   ├── __init__.py
│   └── db.py           # MySQL connection helper
└── templates/
    ├── base.html               # Base layout (navbar, Bootstrap)
    ├── index.html              # Dashboard
    ├── tournaments.html        # Tournament list
    ├── create_tournament.html  # New tournament form
    ├── edit_tournament.html    # Edit tournament form
    ├── tournament_detail.html  # Tournament detail w/ teams, fixtures, leaderboard
    ├── add_team.html           # Add team + players form
    ├── edit_team.html          # Edit team + players form
    ├── team_detail.html        # Team roster view
    ├── setup_map_pool.html     # Map pool configuration
    ├── manage_fixture.html     # Fixture lifecycle management
    ├── manage_winner.html      # Tiebreaker / manual winner selection
    ├── manage_data.html        # Maps, officials, servers admin
    └── view_all_data.html      # Full data overview
```

## License

This project was built as a coursework project. Feel free to use it as a reference.
