package com.example.springbootbackend.mapper;

import com.example.springbootbackend.entity.Positions;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Select;
import java.util.List;


@Mapper
public interface PositionsMapper {
    @Select("SELECT * FROM positions order by sort_order, id")
    List<Positions> getAllPositions();
    @Select("SELECT * FROM positions order by sort_order")
    List<Positions> getAllPositionsOrderBySortOrder();

}
