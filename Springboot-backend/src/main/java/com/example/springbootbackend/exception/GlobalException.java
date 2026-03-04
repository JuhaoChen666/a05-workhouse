package com.example.springbootbackend.exception;

import com.example.springbootbackend.utils.Result;
import org.springframework.web.bind.annotation.ControllerAdvice;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.ResponseBody;

@ControllerAdvice
public class GlobalException {
    @ExceptionHandler(ServiceException.class)
    @ResponseBody
    public Result ServiceException(ServiceException e){
        return Result.error("500",e.getMessage());

    }
}
