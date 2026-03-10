package com.example.springbootbackend.mapper;

import com.example.springbootbackend.entity.Positions;
import org.apache.ibatis.annotations.Delete;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Select;
import java.util.List;


@Mapper
public interface PositionsMapper {
    @Select("SELECT * FROM positions order by sort_order, id")
    List<Positions> getAllPositions();
    @Select("SELECT * FROM positions order by sort_order")
    List<Positions> getAllPositionsOrderBySortOrder();
    @Delete("DELETE FROM positions WHERE id = #{id}")
    int deletePosition(int id);

}
