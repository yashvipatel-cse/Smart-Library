package com.library.backend.controller;

import com.library.backend.model.Book;
import com.library.backend.service.BookLookupService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;
import java.util.*;

/**
 * BookController — Camera Scan (OCR) path.
 * POST /api/match  — receives book numbers detected by OCR, returns book info
 * GET  /api/books/search?q=  — quick search
 */
@RestController
@CrossOrigin(origins = "*", allowedHeaders = "*")
@RequestMapping("/api")
public class BookController {

    @Autowired
    private BookLookupService bookLookupService;

    @PostMapping("/match")
    public Map<String, Object> match(@RequestBody Map<String, Object> req) {
        @SuppressWarnings("unchecked")
        List<String> codes = (List<String>) req.get("codes");
        if (codes == null) codes = new ArrayList<>();

        List<Map<String, Object>> result = new ArrayList<>();
        for (String raw : codes) {
            String code = raw.trim().toUpperCase();
            Map<String, Object> obj = new LinkedHashMap<>();

            Book found = bookLookupService.findByBookNumber(code);
            if (found == null) {
                try {
                    int n = Integer.parseInt(code.substring(1));
                    for (String fmt : new String[]{
                        "B"+String.format("%04d",n),"B"+String.format("%03d",n),"B"+n}) {
                        found = bookLookupService.findByBookNumber(fmt);
                        if (found != null) break;
                    }
                } catch (Exception ignored) {}
            }

            if (found != null) {
                obj.put("found",         true);
                obj.put("bookNumber",    found.getBookNumber());
                obj.put("title",         found.getTitle());
                obj.put("author",        found.getAuthor());
                obj.put("programme",     found.getProgramme());
                obj.put("subject",       found.getSubject());
                obj.put("rack",          found.getRack());
                obj.put("expectedShelf", found.getExpectedShelf());
                obj.put("source",        "OCR");
            } else {
                obj.put("found", false);
                obj.put("code",  code);
                obj.put("status","UNKNOWN");
                obj.put("source","OCR");
            }
            result.add(obj);
        }
        Map<String, Object> resp = new HashMap<>();
        resp.put("books_from_db", result);
        return resp;
    }

    @GetMapping("/books/search")
    public List<Map<String, Object>> search(@RequestParam String q) {
        String query = q.trim().toUpperCase();
        List<Map<String, Object>> out = new ArrayList<>();
        for (Book b : bookLookupService.getAllBooks()) {
            if (b.getBookNumber().contains(query)
                    || b.getTitle().toUpperCase().contains(query)
                    || (b.getAuthor()!=null && b.getAuthor().toUpperCase().contains(query))) {
                Map<String, Object> m = new LinkedHashMap<>();
                m.put("bookNumber",    b.getBookNumber());
                m.put("title",         b.getTitle());
                m.put("author",        b.getAuthor());
                m.put("rack",          b.getRack());
                m.put("expectedShelf", b.getExpectedShelf());
                out.add(m);
                if (out.size() >= 20) break;
            }
        }
        return out;
    }
}
