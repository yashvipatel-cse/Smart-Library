package com.library.backend.controller;

import com.library.backend.model.Book;
import com.library.backend.service.BookLookupService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.*;

/**
 * RFID Controller — uses the unified `books` table.
 *
 * POST /api/scan          ← ESP32 hardware sends scanned UID
 * POST /api/rfid/lookup   ← Frontend sends UID for full details
 * GET  /api/rfid/books    ← Frontend lists all RFID-registered books
 * GET  /api/books/all     ← Frontend lists ALL books (for camera registry)
 */
@RestController
@CrossOrigin(origins = "*", allowedHeaders = "*")
@RequestMapping("/api")
public class RfidController {

    @Autowired
    private BookLookupService bookLookupService;

    // ── POST /api/scan ─────────────────────────────────────────
    // Called by ESP32. Body: { "uid": "FA7819C1", "shelfId": "A1" }
    // Returns plain text: "OK", "WRONG", or "UNKNOWN"
    @PostMapping("/scan")
    public String scan(@RequestBody Map<String, String> req) {
        String uid     = req.getOrDefault("uid", "").trim().toUpperCase();
        String shelfId = req.getOrDefault("shelfId", "").trim().toUpperCase();

        System.out.println("[RFID] Scan — UID: " + uid + "  Shelf: " + shelfId);

        if (uid.isEmpty()) return "UNKNOWN";

        Book book = bookLookupService.findByUid(uid);
        if (book == null) {
            System.out.println("[RFID] UID not found: " + uid);
            return "UNKNOWN";
        }

        boolean correct = book.getExpectedShelf().equalsIgnoreCase(shelfId);
        System.out.println("[RFID] " + (correct ? "✅ OK" : "❌ WRONG") +
                " — " + book.getTitle() +
                " expected=" + book.getExpectedShelf() + " got=" + shelfId);
        return correct ? "OK" : "WRONG";
    }

    // ── POST /api/rfid/lookup ──────────────────────────────────
    // Frontend sends UID + optional shelfId, gets full book details.
    @PostMapping("/rfid/lookup")
    public Map<String, Object> lookup(@RequestBody Map<String, String> req) {
        String uid     = req.getOrDefault("uid", "").trim().toUpperCase();
        String shelfId = req.getOrDefault("shelfId", "").trim().toUpperCase();

        Map<String, Object> response = new HashMap<>();
        Book book = bookLookupService.findByUid(uid);

        if (book == null) {
            response.put("found",   false);
            response.put("uid",     uid);
            response.put("message", "Book not registered — no RFID sticker assigned yet");
            return response;
        }

        boolean correct = shelfId.isEmpty() ||
                book.getExpectedShelf().equalsIgnoreCase(shelfId);

        response.put("found",         true);
        response.put("uid",           uid);
        response.put("bookNumber",    book.getBookNumber());
        response.put("title",         book.getTitle());
        response.put("author",        book.getAuthor());
        response.put("programme",     book.getProgramme());
        response.put("subject",       book.getSubject());
        response.put("rack",          book.getRack());
        response.put("expectedShelf", book.getExpectedShelf());
        response.put("currentShelf",  shelfId.isEmpty() ? book.getExpectedShelf() : shelfId);
        response.put("status",        correct ? "OK" : "WRONG");
        response.put("source",        "RFID");
        return response;
    }

    // ── GET /api/rfid/books ────────────────────────────────────
    // Returns only books that have an RFID sticker assigned.
    @GetMapping("/rfid/books")
    public List<Map<String, Object>> getRfidBooks() {
        return bookLookupService.getRfidBooks().stream().map(b -> {
            Map<String, Object> obj = new LinkedHashMap<>();
            obj.put("uid",           b.getRfidUid());
            obj.put("bookNumber",    b.getBookNumber());
            obj.put("title",         b.getTitle());
            obj.put("author",        b.getAuthor());
            obj.put("programme",     b.getProgramme());
            obj.put("rack",          b.getRack());
            obj.put("expectedShelf", b.getExpectedShelf());
            return obj;
        }).toList();
    }

    // ── GET /api/books/all ─────────────────────────────────────
    // Returns ALL books in the unified table (8421 total).
    @GetMapping("/books/all")
    public List<Map<String, Object>> getAllBooks() {
        return bookLookupService.getAllBooks().stream().map(b -> {
            Map<String, Object> obj = new LinkedHashMap<>();
            obj.put("bookNumber",    b.getBookNumber());
            obj.put("rfidUid",       b.getRfidUid());   // null if no sticker
            obj.put("title",         b.getTitle());
            obj.put("author",        b.getAuthor());
            obj.put("programme",     b.getProgramme());
            obj.put("subject",       b.getSubject());
            obj.put("rack",          b.getRack());
            obj.put("expectedShelf", b.getExpectedShelf());
            return obj;
        }).toList();
    }
}
