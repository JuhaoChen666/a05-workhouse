package com.example.springbootbackend.entity;


import lombok.Data;

@Data
public class Role {
    private Integer id;
    private String name;
    public Role(Integer id, String name) {
        this.id = id;
        this.name = name;
    }

}
