package com.library.backend.model;

import jakarta.persistence.*;

/**
 * JPA Entity for the unified `books` table.
 * Used by BOTH Camera Scan (book_number) and RFID Scan (rfid_uid).
 *
 * Columns:
 *   book_number    → camera OCR reads this label code (e.g. B001)
 *   rfid_uid       → RFID tag UID scanned by ESP32 (NULL until sticker applied)
 *   title, author  → bibliographic info
 *   programme      → academic programme/discipline
 *   subject        → detailed subject for shelf routing
 *   rack           → physical rack label (e.g. Rack-1)
 *   expected_shelf → shelf ID (e.g. A1)
 */
@Entity
@Table(name = "books")
public class Book {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "book_number", unique = true)
    private String bookNumber;          // e.g. B001

    @Column(name = "rfid_uid", unique = true)
    private String rfidUid;             // e.g. FA7819C1 (nullable)

    private String title;
    private String author;
    private String programme;           // e.g. "Computer Engineering (B.Tech)"
    private String subject;             // detailed subject for shelf routing

    private String rack;                // e.g. "Rack-1"

    @Column(name = "expected_shelf")
    private String expectedShelf;       // e.g. "A1"

    // ── Getters & Setters ──────────────────────────────────────
    public Long   getId()                         { return id; }
    public void   setId(Long id)                  { this.id = id; }

    public String getBookNumber()                 { return bookNumber; }
    public void   setBookNumber(String b)         { this.bookNumber = b; }

    public String getRfidUid()                    { return rfidUid; }
    public void   setRfidUid(String r)            { this.rfidUid = r; }

    public String getTitle()                      { return title; }
    public void   setTitle(String t)              { this.title = t; }

    public String getAuthor()                     { return author; }
    public void   setAuthor(String a)             { this.author = a; }

    public String getProgramme()                  { return programme; }
    public void   setProgramme(String p)          { this.programme = p; }

    public String getSubject()                    { return subject; }
    public void   setSubject(String s)            { this.subject = s; }

    public String getRack()                       { return rack; }
    public void   setRack(String r)               { this.rack = r; }

    public String getExpectedShelf()              { return expectedShelf; }
    public void   setExpectedShelf(String e)      { this.expectedShelf = e; }
}
