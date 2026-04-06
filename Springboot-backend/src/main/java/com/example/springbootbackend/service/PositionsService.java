package com.example.springbootbackend.service;

import com.example.springbootbackend.entity.Positions;
import com.example.springbootbackend.entity.Positions_Info;
import com.example.springbootbackend.mapper.PositionsMapper;
import com.example.springbootbackend.mapper.Positions_infoMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

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
    
    // 分页查询和模糊查找
    public Map<String, Object> getPositionsByPage(String name, int page, int pageSize) {
        int offset = (page - 1) * pageSize;
        List<Positions> positions = positionsMapper.getPositionsByPage(name, offset, pageSize);
        int total = positionsMapper.countPositions(name);
        
        Map<String, Object> result = new HashMap<>();
        result.put("list", positions);
        result.put("total", total);
        return result;
    }
    
    // 添加岗位
    public int addPosition(Positions position) {
        return positionsMapper.addPosition(position);
    }
    
    // 添加岗位信息
    public int addPositionInfo(Positions_Info positionInfo) {
        positionInfo.setCreate_time(new Date());
        positionInfo.setUpdate_time(new Date());
        return positions_infoMapper.addPositionInfo(positionInfo);
    }
    
    // 更新岗位信息
    public int updatePositionInfo(Positions_Info positionInfo) {
        positionInfo.setUpdate_time(new Date());
        return positions_infoMapper.updatePositionInfo(positionInfo);
    }
    
    // 删除岗位（同时删除岗位信息）
    public int deletePosition(Integer id) {
        // 先删除岗位信息
        positions_infoMapper.deletePositionInfo(id);
        // 再删除岗位
        return positionsMapper.deletePosition(id);
    }
}