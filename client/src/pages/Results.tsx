import React, { useState, useEffect } from 'react';
import { 
  Card, 
  Select, 
  Button, 
  Space, 
  Typography, 
  message,
  Spin,
  Table,
  Tag,
  Input
} from 'antd';
import { SearchOutlined, TrophyOutlined, UserOutlined } from '@ant-design/icons';
import axios from 'axios';

const { Title } = Typography;
const { Option } = Select;

interface Result {
  id: number;
  athlete_name: string;
  athlete_country: string;
  place: number;
  mark: string;
  wind: number;
  points: number;
  qualified: boolean;
  race_date: string;
  race_type: string;
  event_title: string;
  discipline_name: string;
  category: string;
  competition_name: string;
  venue: string;
}

interface Competition {
  id: number;
  name: string;
}

const Results: React.FC = () => {
  const [results, setResults] = useState<Result[]>([]);
  const [competitions, setCompetitions] = useState<Competition[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedCompetition, setSelectedCompetition] = useState<number | null>(null);
  const [searchText, setSearchText] = useState('');

  useEffect(() => {
    fetchCompetitions();
  }, []);

  useEffect(() => {
    if (selectedCompetition) {
      fetchResults();
    }
  }, [selectedCompetition]);

  const fetchCompetitions = async () => {
    try {
      const response = await axios.get('http://localhost:5000/api/competitions', {
        params: { per_page: 1000 } // Get all competitions
      });
      setCompetitions(response.data.competitions);
    } catch (error) {
      message.error('Failed to fetch competitions');
      console.error('Error fetching competitions:', error);
    }
  };

  const fetchResults = async () => {
    if (!selectedCompetition) return;
    
    setLoading(true);
    try {
      const response = await axios.get(`http://localhost:5000/api/competitions/${selectedCompetition}/results`, {
        params: { per_page: 500 } // Get more results for the competition
      });
      setResults(response.data.results);
    } catch (error) {
      message.error('Failed to fetch results');
      console.error('Error fetching results:', error);
    } finally {
      setLoading(false);
    }
  };

  const filteredResults = results.filter(result =>
    result.athlete_name.toLowerCase().includes(searchText.toLowerCase()) ||
    result.event_title.toLowerCase().includes(searchText.toLowerCase()) ||
    result.discipline_name.toLowerCase().includes(searchText.toLowerCase())
  );

  const columns = [
    {
      title: 'Place',
      dataIndex: 'place',
      key: 'place',
      width: 80,
      render: (place: number) => (
        <Tag color={place <= 3 ? 'gold' : place <= 8 ? 'blue' : 'default'}>
          {place}
        </Tag>
      ),
    },
    {
      title: 'Athlete',
      key: 'athlete',
      render: (record: Result) => (
        <Space direction="vertical" size="small">
          <div>
            <UserOutlined /> <strong>{record.athlete_name}</strong>
          </div>
          <div style={{ fontSize: '12px', color: '#666' }}>
            {record.athlete_country}
          </div>
        </Space>
      ),
    },
    {
      title: 'Event',
      key: 'event',
      render: (record: Result) => (
        <Space direction="vertical" size="small">
          <div><strong>{record.event_title}</strong></div>
          <div style={{ fontSize: '12px', color: '#666' }}>
            <Tag color="purple">{record.discipline_name}</Tag>
            {record.category && <Tag color="green">{record.category}</Tag>}
          </div>
        </Space>
      ),
    },
    {
      title: 'Mark',
      dataIndex: 'mark',
      key: 'mark',
      render: (mark: string) => <strong>{mark}</strong>,
    },
    {
      title: 'Wind',
      dataIndex: 'wind',
      key: 'wind',
      width: 80,
      render: (wind: number) => wind ? `${wind} m/s` : '-',
    },
    {
      title: 'Points',
      dataIndex: 'points',
      key: 'points',
      width: 80,
      render: (points: number) => points ? points.toFixed(0) : '-',
    },
    {
      title: 'Qualified',
      dataIndex: 'qualified',
      key: 'qualified',
      width: 100,
      render: (qualified: boolean) => (
        <Tag color={qualified ? 'success' : 'default'}>
          {qualified ? 'Yes' : 'No'}
        </Tag>
      ),
    },
    {
      title: 'Date',
      dataIndex: 'race_date',
      key: 'race_date',
      width: 120,
      render: (date: string) => new Date(date).toLocaleDateString(),
    },
  ];

  return (
    <div>
      <Title level={2}>Competition Results</Title>
      
      <Card style={{ marginBottom: 16 }}>
        <Space direction="vertical" style={{ width: '100%' }}>
          <div>
            <strong>Select Competition:</strong>
            <Select
              style={{ width: 400, marginLeft: 16 }}
              placeholder="Choose a competition to view results"
              value={selectedCompetition}
              onChange={setSelectedCompetition}
              showSearch
              filterOption={(input, option) =>
                option?.children?.toString().toLowerCase().includes(input.toLowerCase()) ?? false
              }
            >
              {competitions.map(competition => (
                <Option key={competition.id} value={competition.id}>
                  {competition.name}
                </Option>
              ))}
            </Select>
          </div>
          
          {selectedCompetition && (
            <div>
              <strong>Search Results:</strong>
              <Input
                style={{ width: 300, marginLeft: 16 }}
                placeholder="Search by athlete, event, or discipline..."
                prefix={<SearchOutlined />}
                value={searchText}
                onChange={(e) => setSearchText(e.target.value)}
              />
            </div>
          )}
        </Space>
      </Card>

      {selectedCompetition ? (
        <Card>
          <Table
            columns={columns}
            dataSource={filteredResults}
            rowKey="id"
            loading={loading}
            pagination={{
              pageSize: 50,
              showSizeChanger: true,
              showQuickJumper: true,
              showTotal: (total, range) =>
                `${range[0]}-${range[1]} of ${total} results`,
            }}
            scroll={{ x: 1000 }}
          />
        </Card>
      ) : (
        <Card>
          <div style={{ 
            textAlign: 'center', 
            padding: '50px',
            color: '#666'
          }}>
            <TrophyOutlined style={{ fontSize: 48, marginBottom: 16 }} />
            <div>Select a competition to view results</div>
          </div>
        </Card>
      )}
    </div>
  );
};

export default Results;
