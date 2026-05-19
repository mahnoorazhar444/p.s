# HabitFlow – UML Diagrams & Architectural Documentation

This document contains a complete set of professional UML diagrams detailing the structure, architecture, and behavior of the **HabitFlow – Daily Habit Tracker** application. All diagrams are built using standard, clear Mermaid syntax with straight connections and appropriate UML arrow conventions.

---

## 1. Use Case Diagram
The Use Case diagram shows the interactions between the **General User**, the automatic **System Timer**, and the core functionalities of the application. The associations are represented by standard straight solid lines, while relationship dependencies use dashed arrow lines labeled with `<<include>>` or `<<extend>>` pointing in the correct UML direction.

```mermaid
graph LR
    %% Actors
    ActorUser["User (Actor)"]
    ActorTimer["System Timer"]

    %% Use Cases
    ucRegister(["Register Account"])
    ucLogin(["Login Account"])
    ucViewDash(["View Dashboard"])
    ucMarkDone(["Mark Habit Done"])
    ucAddHabit(["Add Custom Habit"])
    ucViewStats(["View Weekly Stats"])
    ucAdminPanel(["Admin Panel"])

    %% Associations (Straight solid lines)
    ActorUser --- ucRegister
    ActorUser --- ucLogin
    ActorUser --- ucViewDash
    ActorUser --- ucMarkDone
    ActorUser --- ucAddHabit
    ActorUser --- ucViewStats
    ActorUser --- ucAdminPanel

    ActorTimer --- ucViewDash

    %% Relationships (Dashed include arrows pointing to base requirement)
    ucViewDash -.->|"<<include>>"| ucLogin
    ucMarkDone -.->|"<<include>>"| ucLogin
    ucAddHabit -.->|"<<include>>"| ucLogin
    ucViewStats -.->|"<<include>>"| ucLogin
    ucAdminPanel -.->|"<<include>>"| ucLogin
```

---

## 2. Class Diagram
The Class diagram represents the Object-Oriented Programming (OOP) structure of the application. It highlights encapsulation, inheritance (screens inheriting from the base `Panel` class which inherits from `tk.Frame`), and associations between managers and database operations.

```mermaid
classDiagram
    class DatabaseManager {
        +db_name : str
        +conn : Connection
        +init_db()
        +get_connection() : Connection
        +execute_query(query: str, params: tuple) : Cursor
        +fetch_all(query: str, params: tuple) : list
        +fetch_one(query: str, params: tuple) : tuple
    }

    class User {
        +db : DatabaseManager
        +current_user_id : int
        +current_username : str
        +hash_password(password: str) : str
        +register(username: str, password: str) : bool
        +login(username: str, password: str) : bool
        +logout()
    }

    class Habit {
        +id : int
        +user_id : int
        +name : str
        +category : str
        +difficulty : str
        +streak : int
        +last_completed : str
    }

    class StreakManager {
        <<utility>>
        +check_and_update_streak(habit: Habit, db: DatabaseManager, today: str) : int
        +increment_streak(habit: Habit, db: DatabaseManager, today: str)
    }

    class Timer {
        +root : Tk
        +label : Label
        +reset_callback : function
        +update_clock()
    }

    class ReportManager {
        +db : DatabaseManager
        +user_id : int
        +calculate_weekly_stats() : tuple
        +save_report(percent: float, grade: str, feedback: str)
    }

    class Admin {
        +db : DatabaseManager
        +user_id : int
        +add_habit(name: str, category: str, difficulty: str)
        +edit_habit(habit_id: int, new_name: str)
        +delete_habit(habit_id: int)
    }

    class Panel {
        +app : HabitApp
    }

    class HabitApp {
        +db_manager : DatabaseManager
        +user_manager : User
        +style : Style
        +container : Frame
        +show_frame(frame_class)
    }

    %% Inheritance (Generalization)
    Panel <|-- LoginScreen
    Panel <|-- RegisterScreen
    Panel <|-- DashboardScreen
    Panel <|-- AddHabitScreen
    Panel <|-- StatsScreen
    Panel <|-- AdminPanel

    %% Associations & Dependencies
    HabitApp *-- DatabaseManager
    HabitApp *-- User
    User --> DatabaseManager
    ReportManager --> DatabaseManager
    Admin --> DatabaseManager
    StreakManager ..> Habit
    StreakManager ..> DatabaseManager
    DashboardScreen *-- Timer
    DashboardScreen --> StreakManager
    AddHabitScreen --> Admin
    StatsScreen --> ReportManager
    AdminPanel --> Admin
```

---

## 3. Entity Relationship Diagram (ERD)
The ERD shows the SQLite database schema model design, representing primary keys, foreign key constraints, column types, and structural relationship cardinalities.

```mermaid
erDiagram
    users {
        int id PK
        string username UK
        string password_hash
    }
    habits {
        int id PK
        int user_id FK
        string name
        string category
        string difficulty
        int streak
        string last_completed
    }
    daily_log {
        int id PK
        int habit_id FK
        int user_id FK
        string date
        int completed
    }
    reports {
        int id PK
        int user_id FK
        string week_start
        float completion_percent
        string grade
        string feedback
        string saved_on
    }
    categories {
        int id PK
        string name UK
    }

    users ||--o{ habits : "creates"
    users ||--o{ daily_log : "logs"
    users ||--o{ reports : "receives"
    habits ||--o{ daily_log : "tracked_by"
```

---

## 4. Activity Diagram
The Activity diagram models the procedural flow and logic that occurs when a user checks/unchecks a habit card checkbox on their dashboard. It utilizes standard straight routing paths.

```mermaid
flowchart TD
    Start([User clicks Habit Checkbox]) --> CheckStatus{Is Checkbox Checked?}
    
    CheckStatus -->|Yes / Completed| LogDone[Create/Update Daily Log with completed=1]
    LogDone --> IncStreak[Call StreakManager.increment_streak]
    IncStreak --> UpdateDB1[Update habits table: streak + 1, last_completed = today]
    
    CheckStatus -->|No / Uncompleted| LogUndone[Update Daily Log with completed=0]
    LogUndone --> DecStreak[Adjust habit streak: streak - 1]
    DecStreak --> UpdateDB2[Update habits table: streak, last_completed = None]
    
    UpdateDB1 --> Refresh[Refresh Dashboard Screen]
    UpdateDB2 --> Refresh
    Refresh --> End([End Activity])
```

---

## 5. Sequence Diagram
This Sequence diagram models the chronological process flow and system interactions when a user adds a new habit, validating the inputs, storing them to the database, and updating the dashboard screen.

```mermaid
sequenceDiagram
    autonumber
    actor User as General User
    participant View as AddHabitScreen
    participant Ctrl as Admin
    participant DB as DatabaseManager
    participant App as HabitApp
    participant Dash as DashboardScreen

    User->>View: Enter name, category, difficulty
    User->>View: Click "Save"
    activate View
    Note over View: Validate inputs
    alt Name is empty
        View-->>User: Display validation error
    else Name is valid
        View->>Ctrl: add_habit(name, category, difficulty)
        activate Ctrl
        Ctrl->>DB: execute_query("INSERT INTO habits...", params)
        activate DB
        DB-->>Ctrl: Return execution cursor/success
        deactivate DB
        Ctrl-->>View: Success confirmed
        deactivate Ctrl
        View->>App: show_frame(DashboardScreen)
        deactivate View
        activate App
        App->>Dash: Initialize & load
        activate Dash
        Dash->>DB: fetch_all("SELECT FROM habits...", user_id)
        activate DB
        DB-->>Dash: Return list of habits
        deactivate DB
        Dash-->>User: Render Dashboard with new Habit
        deactivate Dash
        deactivate App
    end
```
