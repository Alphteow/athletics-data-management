import React, { useState, useEffect, useMemo } from 'react';
import { 
  Table, 
  Card, 
  Input,
  Select, 
  message, 
  Typography, 
  Row, 
  Col, 
  Spin,
  Button,
  Space,
  Pagination,
  Empty,
  Tag,
  Divider
} from 'antd';
import { UserOutlined, TrophyOutlined, ClearOutlined, ReloadOutlined } from '@ant-design/icons';
import axios from 'axios';
import { auth } from '../firebase';
import { useCache } from '../hooks/useCache';

const { Title, Text } = Typography;
const { Option } = Select;

  interface Athlete {
    id: number;
    full_name: string;
    country_code: string;
    country_name: string;
    birth_date: string;
    gender: string;
  }

  interface AthleteResult {
    id: number;
    place: number;
    mark: string;
    athlete_name: string;
    athlete_country: string;
    race_date: string;
    race_type: string;
    event_name: string;
    discipline_code: string;
    discipline_name: string;
    category: string;
    competition_name: string;
    start_date: string;
  }

interface AthletesResponse {
  athletes: Athlete[];
  pagination: {
    page: number;
    per_page: number;
    total: number;
    pages: number;
  };
}

interface AthleteResultsResponse {
  results: AthleteResult[];
  athlete_id: number;
  page: number;
  per_page: number;
  total: number;
}

const AthleteResults: React.FC = () => {
  const [selectedAthlete, setSelectedAthlete] = useState<number | null>(null);
  const [athletesPage, setAthletesPage] = useState(1);
  const [resultsPage, setResultsPage] = useState(1);
  const [searchText, setSearchText] = useState('');
  const [activeSearchText, setActiveSearchText] = useState('');
  
  // Always use deployed API
  const API_BASE_URL = 'https://athletics-api-450438167261.asia-southeast1.run.app';
  
  // Get auth token helper
  const getAuthHeaders = async () => {
    const user = auth.currentUser;
    if (user) {
      try {
        const token = await user.getIdToken();
        return { Authorization: `Bearer ${token}` };
      } catch (error) {
        console.error('Error getting auth token:', error);
        return {};
      }
    }
    console.warn('No authenticated user found');
    return {};
  };
  
  // Cache for athlete search results (only fetches when activeSearchText changes)
  const { data: athletesData, loading: loadingAthletes, error: athletesError } = useCache<AthletesResponse>(
    `athletes-search-${activeSearchText}-page-${athletesPage}`,
    async () => {
      if (!activeSearchText) return { athletes: [], pagination: { page: 1, per_page: 20, total: 0, pages: 0 } };
      
      const headers = await getAuthHeaders();
      console.log('Searching for athletes:', activeSearchText);
      const response = await axios.get(`${API_BASE_URL}/api/athletes`, {
        params: { 
          search: activeSearchText,
          page: athletesPage,
          per_page: 20, // Reduced for shorter dropdown
          sort_by: 'full_name',
          sort_order: 'ASC'
        },
        headers
      });
      console.log('Athletes API response:', response.data);
      return response.data;
    },
    2 * 60 * 1000 // 2 minutes cache
  );

  // Cache for athlete results
  const { data: resultsData, loading: loadingResults, error: resultsError, refresh: refreshResults } = useCache<AthleteResultsResponse>(
    `athlete-results-${selectedAthlete}-page-${resultsPage}`,
    async () => {
      if (!selectedAthlete) return { results: [], athlete_id: 0, page: 1, per_page: 50, total: 0 };
      
      const headers = await getAuthHeaders();
      const response = await axios.get(`${API_BASE_URL}/api/athletes/${selectedAthlete}/results`, {
        params: { 
          page: resultsPage,
          per_page: 100
        },
        headers
      });
      return response.data;
    },
    2 * 60 * 1000 // 2 minutes cache for results
  );

  // Handle athlete selection
  const handleAthleteSelect = (athleteId: number) => {
    setSelectedAthlete(athleteId);
    setResultsPage(1);
  };

  // Handle pagination changes
  const handleAthletesPageChange = (page: number) => {
    setAthletesPage(page);
  };

  const handleResultsPageChange = (page: number) => {
    setResultsPage(page);
  };

  // Get selected athlete info
  const selectedAthleteInfo = useMemo(() => {
    if (!athletesData?.athletes || !selectedAthlete) return null;
    return athletesData.athletes.find(a => a.id === selectedAthlete);
  }, [athletesData?.athletes, selectedAthlete]);

  // Handle errors
  useEffect(() => {
    if (athletesError) {
      message.error(`Failed to fetch athletes: ${athletesError}`);
    }
  }, [athletesError]);

  useEffect(() => {
    if (resultsError) {
      message.error(`Failed to fetch athlete results: ${resultsError}`);
    }
  }, [resultsError]);

  const columns = [
    {
      title: 'Place',
      dataIndex: 'place',
      key: 'place',
      width: 80,
      render: (place: number) => {
        let color = 'default';
        if (place === 1) color = 'gold';
        else if (place === 2) color = 'silver';
        else if (place === 3) color = 'bronze';
        return <Tag color={color}>{place}</Tag>;
      },
      sorter: (a: AthleteResult, b: AthleteResult) => a.place - b.place,
    },
    {
      title: 'Result',
      dataIndex: 'mark',
      key: 'mark',
      width: 100,
      render: (text: string) => <span style={{ fontFamily: 'monospace' }}>{text}</span>,
    },
      {
        title: 'Event',
        dataIndex: 'event_name',
        key: 'event_name',
        width: 180,
        ellipsis: true,
        sorter: (a: AthleteResult, b: AthleteResult) => a.event_name.localeCompare(b.event_name),
        render: (text: string) => (
          <span title={text} style={{ fontSize: '12px' }}>
            {text}
          </span>
        ),
      },
    {
      title: 'Discipline',
      dataIndex: 'discipline_name',
      key: 'discipline_name',
      width: 180,
      ellipsis: true,
      render: (text: string, record: AthleteResult) => (
        <Space direction="vertical" size={0}>
          <span title={text} style={{ fontSize: '12px' }}>
            {text || record.event_name}
          </span>
          <Tag color="blue" style={{ fontSize: '10px', height: 'auto', lineHeight: '18px' }}>
            {record.category || 'Track & Field'}
          </Tag>
        </Space>
      ),
      sorter: (a: AthleteResult, b: AthleteResult) => (a.discipline_name || a.event_name).localeCompare(b.discipline_name || b.event_name),
    },
    {
      title: 'Competition',
      dataIndex: 'competition_name',
      key: 'competition_name',
      width: 200,
      sorter: (a: AthleteResult, b: AthleteResult) => a.competition_name.localeCompare(b.competition_name),
    },
    {
      title: 'Competition Date',
      dataIndex: 'start_date',
      key: 'start_date',
      width: 120,
      render: (date: string) => new Date(date).toLocaleDateString(),
      sorter: (a: AthleteResult, b: AthleteResult) => new Date(a.start_date).getTime() - new Date(b.start_date).getTime(),
    },
    {
      title: 'Race Date',
      dataIndex: 'race_date',
      key: 'race_date',
      width: 120,
      render: (date: string) => new Date(date).toLocaleDateString(),
      sorter: (a: AthleteResult, b: AthleteResult) => new Date(a.race_date).getTime() - new Date(b.race_date).getTime(),
    },
    {
      title: 'Race Type',
      dataIndex: 'race_type',
      key: 'race_type',
      width: 100,
    },
  ];

  return (
    <div style={{ padding: '0 16px' }}>
      <Title level={2} style={{ marginBottom: 8 }}>
        <UserOutlined style={{ marginRight: 8, color: '#1890ff' }} />
        Athlete Results
      </Title>
      <Text type="secondary" style={{ marginBottom: 24, display: 'block' }}>
        Search for athletes and view their competition results and performance history
      </Text>

      {/* Search Section */}
      <Card 
        title="Search Athletes" 
        style={{ marginBottom: 24 }}
      >
        <Space.Compact style={{ width: '100%' }}>
          <Input
            placeholder="Search athletes by name or country"
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            onPressEnter={() => {
              // Trigger search when Enter is pressed
              setActiveSearchText(searchText);
              setAthletesPage(1);
            }}
            style={{ width: 'calc(100% - 100px)' }}
            size="large"
          />
          <Button 
            type="primary" 
            onClick={() => {
              setActiveSearchText(searchText);
              setAthletesPage(1);
            }}
            loading={loadingAthletes}
            size="large"
          >
            Search
          </Button>
        </Space.Compact>
      </Card>

      {/* Search Results */}
      {athletesData && athletesData.athletes.length > 0 && (
        <Card 
          title={
            <Space>
              <UserOutlined />
              <span>Search Results ({athletesData.pagination.total} athletes found)</span>
            </Space>
          }
          style={{ marginBottom: 24 }}
        >
          <Table
            dataSource={athletesData.athletes}
            rowKey="id"
            size="small"
            pagination={{
              current: athletesPage,
              total: athletesData.pagination.total,
              pageSize: athletesData.pagination.per_page,
              onChange: handleAthletesPageChange,
              showSizeChanger: false,
              showQuickJumper: true,
              showTotal: (total, range) => 
                `${range[0]}-${range[1]} of ${total} athletes`
            }}
            onRow={(record) => ({
              onClick: () => handleAthleteSelect(record.id),
              style: { cursor: 'pointer' }
            })}
          >
            <Table.Column 
              title="Name" 
              dataIndex="full_name" 
              key="name"
              render={(text, record) => (
                <Space>
                  <UserOutlined style={{ color: '#1890ff' }} />
                  <strong>{text}</strong>
                </Space>
              )}
            />
            <Table.Column 
              title="Country" 
              dataIndex="country_name" 
              key="country"
              render={(text, record) => text || record.country_code || 'Unknown'}
            />
            <Table.Column 
              title="Gender" 
              dataIndex="gender" 
              key="gender"
              render={(gender) => {
                if (!gender) return 'Unknown';
                const isMale = gender.toLowerCase() === 'male' || gender === 'M';
                return (
                  <Tag color={isMale ? 'blue' : 'pink'}>
                    {isMale ? 'Male' : 'Female'}
                  </Tag>
                );
              }}
            />
            <Table.Column 
              title="Birth Date" 
              dataIndex="birth_date" 
              key="birth_date"
              render={(date) => date ? new Date(date).toLocaleDateString() : 'Unknown'}
            />
          </Table>
        </Card>
      )}

      {/* Selected Athlete Info */}
      {selectedAthlete && selectedAthleteInfo && (
        <Card 
          style={{ marginBottom: 24, backgroundColor: '#f0f5ff' }}
          bodyStyle={{ padding: '16px 24px' }}
        >
          <Row gutter={16} align="middle">
            <Col span={6}>
              <Space direction="vertical" size={4}>
                <Text type="secondary" style={{ fontSize: '12px' }}>Athlete Name</Text>
                <Text strong style={{ fontSize: '16px' }}>
                  <UserOutlined style={{ marginRight: 8, color: '#1890ff' }} />
                  {selectedAthleteInfo.full_name}
                </Text>
              </Space>
            </Col>
            <Col span={4}>
              <Space direction="vertical" size={4}>
                <Text type="secondary" style={{ fontSize: '12px' }}>Country</Text>
                <Text strong>{selectedAthleteInfo.country_name || selectedAthleteInfo.country_code || 'Unknown'}</Text>
              </Space>
            </Col>
            <Col span={3}>
              <Space direction="vertical" size={4}>
                <Text type="secondary" style={{ fontSize: '12px' }}>Gender</Text>
                <div>
                  {selectedAthleteInfo.gender && (
                    <Tag color={selectedAthleteInfo.gender.toLowerCase() === 'male' || selectedAthleteInfo.gender === 'M' ? 'blue' : 'pink'}>
                      {selectedAthleteInfo.gender.toLowerCase() === 'male' || selectedAthleteInfo.gender === 'M' ? 'Male' : 'Female'}
                    </Tag>
                  )}
                </div>
              </Space>
            </Col>
            <Col span={5}>
              <Space direction="vertical" size={4}>
                <Text type="secondary" style={{ fontSize: '12px' }}>Birth Date</Text>
                <Text>{selectedAthleteInfo.birth_date ? new Date(selectedAthleteInfo.birth_date).toLocaleDateString() : 'Unknown'}</Text>
              </Space>
            </Col>
            <Col span={6} style={{ textAlign: 'right' }}>
              <Space>
                <Tag color="blue" style={{ fontSize: '14px', padding: '4px 12px' }}>
                  <TrophyOutlined style={{ marginRight: 4 }} />
                  {resultsData?.total || 0} Results
                </Tag>
                <Button 
                  icon={<ReloadOutlined />}
                  onClick={refreshResults}
                  loading={loadingResults}
                  size="small"
                >
                  Refresh
                </Button>
              </Space>
            </Col>
          </Row>
        </Card>
      )}

      {/* Results Section */}
      {selectedAthlete && (
        <Card
          title={
            <Space>
              <TrophyOutlined />
              <span>Competition Results</span>
            </Space>
          }
        >
          {loadingResults ? (
            <div style={{ textAlign: 'center', padding: '50px' }}>
              <Spin size="large" />
              <div style={{ marginTop: 16 }}>Loading athlete results...</div>
            </div>
          ) : resultsData?.results.length === 0 ? (
            <Empty 
              description="No results found for this athlete"
              image={Empty.PRESENTED_IMAGE_SIMPLE}
            />
          ) : (
            <>
              <Table
                columns={columns}
                dataSource={resultsData?.results || []}
                rowKey="id"
                pagination={false}
                scroll={{ x: 1200, y: 400 }}
                size="small"
                style={{ marginBottom: 16 }}
              />
              
              {resultsData && resultsData.total > resultsData.per_page && (
                <div style={{ textAlign: 'center' }}>
                  <Pagination
                    current={resultsPage}
                    total={resultsData.total}
                    pageSize={resultsData.per_page}
                    onChange={handleResultsPageChange}
                    showSizeChanger={false}
                    showQuickJumper
                    showTotal={(total, range) => 
                      `${range[0]}-${range[1]} of ${total} results`
                    }
                  />
                </div>
              )}
            </>
          )}
        </Card>
      )}

      {!selectedAthlete && !activeSearchText && (
        <Card>
          <Empty 
            description="Search for an athlete above to view their results"
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          />
        </Card>
      )}

      {!selectedAthlete && activeSearchText && athletesData && athletesData.athletes.length === 0 && (
        <Card>
          <Empty 
            description={`No athletes found matching "${activeSearchText}"`}
            image={Empty.PRESENTED_IMAGE_SIMPLE}
          />
        </Card>
      )}
    </div>
  );
};

export default AthleteResults;