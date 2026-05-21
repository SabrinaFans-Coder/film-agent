from app.services.csv_parser import parse_csv, ParsedRow


def test_parse_csv_valid():
    csv_content = (
        "豆瓣ID,标题,IMDb ID,上映日期,标记日期,我的评分,我的评价,条目链接\n"
        "35010610,挽救计划,tt12042730,2026/3/13,2026/5/16,5,好看,https://movie.douban.com/subject/35010610/\n"
        "26816519,逃避虽可耻但有用,tt5917100,2016/10/11,2026/4/26,5,很舒服,https://movie.douban.com/subject/26816519/\n"
    )
    rows = parse_csv(csv_content.encode("utf-8-sig"))
    assert len(rows) == 2
    assert rows[0].title == "挽救计划"
    assert rows[0].imdb_id == "tt12042730"
    assert rows[0].rating == 5.0
    assert rows[0].year == 2026
    assert rows[0].review == "好看"


def test_parse_csv_empty_fields():
    csv_content = (
        "豆瓣ID,标题,IMDb ID,上映日期,标记日期,我的评分,我的评价,条目链接\n"
        "12345,无IMDb电影,,2020/5/10,2026/1/1,3,,https://movie.douban.com/subject/12345/\n"
    )
    rows = parse_csv(csv_content.encode("utf-8-sig"))
    assert rows[0].imdb_id is None
    assert rows[0].review is None
    assert rows[0].rating == 3.0
    assert rows[0].year == 2020


def test_parse_csv_date_formats():
    csv_content = (
        "豆瓣ID,标题,IMDb ID,上映日期,标记日期,我的评分,我的评价,条目链接\n"
        "1,测试,tt1,2025/1/1,2026-05-20,4,,https://a\n"
        "2,测试2,tt2,,2026/5/16,,,https://b\n"
    )
    rows = parse_csv(csv_content.encode("utf-8-sig"))
    assert rows[0].release_date == "2025-01-01"
    assert rows[0].tagged_date == "2026-05-20"
    assert rows[1].release_date is None
