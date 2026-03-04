package com.example.springbootbackend.exception;

public class ServiceException extends RuntimeException {
    public ServiceException(String message) {
     super(message);
    }
}
