package com.example.springbootbackend.service;

import com.example.springbootbackend.entity.Positions;
import com.example.springbootbackend.entity.Positions_Info;
import com.example.springbootbackend.mapper.PositionsMapper;
import com.example.springbootbackend.mapper.Positions_infoMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class PositionsService {
    @Autowired
    private PositionsMapper positionsMapper;
    @Autowired
    private Positions_infoMapper positions_infoMapper;

    public List<Positions> getAllPositions() {
        return positionsMapper.getAllPositions();
    }
    public Positions_Info getPosition_InfoById(Integer id) {
        return positions_infoMapper.getPositions_InfoById(id);
    }
    public int deletePosition(Integer id) {
        return positionsMapper.deletePosition(id);
    }
}
