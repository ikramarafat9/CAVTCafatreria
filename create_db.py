﻿import sqlite3

def create_database(db_path='college_users.db'):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.executescript("""
    DROP TABLE IF EXISTS order_details;
    DROP TABLE IF EXISTS orders;
    DROP TABLE IF EXISTS item_customizable_options;
    DROP TABLE IF EXISTS customizable_options;
    DROP TABLE IF EXISTS customizable_ingredients;
    DROP TABLE IF EXISTS item_fixed_ingredients;
    DROP TABLE IF EXISTS fixed_ingredients;
    DROP TABLE IF EXISTS MenuItem;
    DROP TABLE IF EXISTS category;
    DROP TABLE IF EXISTS Feedback;
    DROP TABLE IF EXISTS User;
    DROP TABLE IF EXISTS Role;

    CREATE TABLE category (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL
    );

    CREATE TABLE MenuItem (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category_id INTEGER NOT NULL,
        price REAL NOT NULL,
        image TEXT,
        FOREIGN KEY (category_id) REFERENCES category(id) ON DELETE CASCADE
    );

    CREATE TABLE fixed_ingredients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL
    );

    CREATE TABLE item_fixed_ingredients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id INTEGER NOT NULL,
        fixed_ingredient_id INTEGER NOT NULL,
        FOREIGN KEY (item_id) REFERENCES MenuItem(id) ON DELETE CASCADE,
        FOREIGN KEY (fixed_ingredient_id) REFERENCES fixed_ingredients(id) ON DELETE CASCADE
    );

    CREATE TABLE customizable_ingredients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL
    );

    CREATE TABLE customizable_options (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customizable_ingredient_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        extra_price REAL DEFAULT 0,
        FOREIGN KEY (customizable_ingredient_id) REFERENCES customizable_ingredients(id) ON DELETE CASCADE
    );

    CREATE TABLE item_customizable_options (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id INTEGER NOT NULL,
        customizable_option_id INTEGER NOT NULL,
        FOREIGN KEY (item_id) REFERENCES MenuItem(id) ON DELETE CASCADE,
        FOREIGN KEY (customizable_option_id) REFERENCES customizable_options(id) ON DELETE CASCADE
    );

    CREATE TABLE orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        order_time TEXT NOT NULL
    );

    CREATE TABLE order_details (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        item_id INTEGER NOT NULL,
        quantity INTEGER DEFAULT 1,
        base_price REAL NOT NULL,
        extra_price REAL DEFAULT 0,
        details_json TEXT,
        FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
        FOREIGN KEY (item_id) REFERENCES MenuItem(id) ON DELETE CASCADE
    );

    CREATE TABLE Feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        content TEXT NOT NULL,
        feedback_date DATETIME DEFAULT CURRENT_TIMESTAMP,
        user_id INTEGER NOT NULL,
        FOREIGN KEY(user_id) REFERENCES User(id) ON DELETE CASCADE
    );

    CREATE TABLE Role (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE CHECK(name IN ('مدير', 'موظف', 'طالب', 'صاحب الكافتيريا'))
    );

    CREATE TABLE User (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        specialty TEXT NOT NULL CHECK(specialty IN (
            'مهارات إنتاج المخبوزات والحلويات والمعجنات',
            'صانع حلويات شرقية',
            'صانع حلويات غربية',
            'صانع معجنات',
            'حلاق شعر نسائي / كوافيرة أو كوافير',
            'مساعد حلاق نسائي',
            'مدير',
            'مساعد تجميل',
            'مختص مكياج',
            'منسق إداري طبي',
            'حاضنة أطفال',
            'خياط ملابس نسائية',
            'مشغل / آلة درزة صناعية',
            'مدخل بيانات',
            'مطور التطبيقات المتقدمة',
            'تكنولوجيا إدارة النظم والشبكات',
            'صيانة أنظمة ومعدات تقنية المعلومات',
            'تكنولوجيا الرسم الهندسي وتطبيقاته'
        )),
        password TEXT NOT NULL,
        phone_number TEXT NOT NULL CHECK(length(phone_number) = 10),
        role_id INTEGER NOT NULL DEFAULT 3,
        FOREIGN KEY(role_id) REFERENCES Role(id) ON DELETE CASCADE
    );
    """)

    conn.commit()
    conn.close()
    print("Database and tables 'college_users' created successfully!")

if __name__ == "__main__":
    create_database()
