package com.library.backend.service;

import com.library.backend.model.Book;
import com.library.backend.model.BookRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Optional;

/**
 * Central lookup service for the unified books table.
 * Supports BOTH Camera Scan (by book_number) and RFID Scan (by rfid_uid).
 */
@Service
public class BookLookupService {

    @Autowired
    private BookRepository bookRepository;

    /** Called by RFID controller — ESP32 sends UID */
    public Book findByUid(String uid) {
        Optional<Book> book = bookRepository.findByRfidUidIgnoreCase(uid);
        return book.orElse(null);
    }

    /** Called by Camera scan controller — OCR reads book number */
    public Book findByBookNumber(String bookNumber) {
        Optional<Book> book = bookRepository.findByBookNumberIgnoreCase(bookNumber);
        return book.orElse(null);
    }

    /** All books — for dashboard/registry listing */
    public List<Book> getAllBooks() {
        return bookRepository.findAll();
    }

    /** Only books that have an RFID UID assigned */
    public List<Book> getRfidBooks() {
        return bookRepository.findAll().stream()
                .filter(b -> b.getRfidUid() != null && !b.getRfidUid().isBlank())
                .toList();
    }
}
