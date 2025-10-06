import React, { useState, useEffect } from 'react';
import { 
  Card, 
  Row, 
  Col, 
  Statistic, 
  Typography, 
  message,
  Spin,
  Select,
  Table
} from 'antd';
import { 
  TrophyOutlined, 
  TeamOutlined, 
  BarChartOutlined, 
  CalendarOutlined,
  FlagOutlined
} from '@ant-design/icons';
import axios from 'axios';

const { Title } = Typography;
const { Option } = Select;

interface Stats {
  competitions: number;
  athletes: number;
  results: number;
  events: number;
}

interface Country {
  code: string;
  name: string;
}

interface Discipline {
  discipline_code: string;
  discipline_name: string;
  category: string;
}

const Stats: React.FC = () => {
  const [stats, setStats] = useState<Stats | null>(null);
  const [countries, setCountries] = useState<Country[]>([]);
  const [disciplines, setDisciplines] = useState<Discipline[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedCountry, setSelectedCountry] = useState<string>('all');
  const [selectedDiscipline, setSelectedDiscipline] = useState<string>('all');

  useEffect(() => {
    fetchAllData();
  }, []);

  const fetchAllData = async () => {
    try {
      const [statsResponse, countriesResponse, disciplinesResponse] = await Promise.all([
        axios.get('http://localhost:5000/api/stats'),
        axios.get('http://localhost:5000/api/countries'),
        axios.get('http://localhost:5000/api/disciplines')
      ]);

      setStats(statsResponse.data);
      setCountries(countriesResponse.data.countries);
      setDisciplines(disciplinesResponse.data.disciplines);
    } catch (error) {
      message.error('Failed to fetch statistics data');
      console.error('Error fetching stats:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Spin size="large" />
      </div>
    );
  }

  const disciplineCategories = [...new Set(disciplines.map(d => d.category))];

  const disciplineColumns = [
    {
      title: 'Discipline Code',
      dataIndex: 'discipline_code',
      key: 'discipline_code',
    },
    {
      title: 'Discipline Name',
      dataIndex: 'discipline_name',
      key: 'discipline_name',
    },
    {
      title: 'Category',
      dataIndex: 'category',
      key: 'category',
      render: (category: string) => (
        <span style={{ 
          backgroundColor: '#f0f0f0', 
          padding: '2px 8px', 
          borderRadius: '4px',
          fontSize: '12px'
        }}>
          {category}
        </span>
      ),
    },
  ];

  return (
    <div>
      <Title level={2}>Database Statistics & Information</Title>
      
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Total Competitions"
              value={stats?.competitions || 0}
              prefix={<TrophyOutlined />}
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Total Athletes"
              value={stats?.athletes || 0}
              prefix={<TeamOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Total Results"
              value={stats?.results || 0}
              prefix={<BarChartOutlined />}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Total Events"
              value={stats?.events || 0}
              prefix={<CalendarOutlined />}
              valueStyle={{ color: '#f5222d' }}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card title="Countries in Database" extra={<FlagOutlined />}>
            <div style={{ maxHeight: 300, overflowY: 'auto' }}>
              {countries.map((country, index) => (
                <div key={country.code} style={{ 
                  padding: '8px 0',
                  borderBottom: index < countries.length - 1 ? '1px solid #f0f0f0' : 'none'
                }}>
                  <strong>{country.name}</strong> ({country.code})
                </div>
              ))}
            </div>
            <div style={{ marginTop: 16, textAlign: 'center', color: '#666' }}>
              Total: {countries.length} countries
            </div>
          </Card>
        </Col>
        
        <Col xs={24} lg={12}>
          <Card title="Discipline Categories" extra={<BarChartOutlined />}>
            <div style={{ maxHeight: 300, overflowY: 'auto' }}>
              {disciplineCategories.map((category, index) => (
                <div key={category} style={{ 
                  padding: '8px 0',
                  borderBottom: index < disciplineCategories.length - 1 ? '1px solid #f0f0f0' : 'none'
                }}>
                  <span style={{ 
                    backgroundColor: '#e6f7ff', 
                    padding: '4px 8px', 
                    borderRadius: '4px',
                    fontSize: '12px',
                    marginRight: 8
                  }}>
                    {category}
                  </span>
                  {disciplines.filter(d => d.category === category).length} disciplines
                </div>
              ))}
            </div>
            <div style={{ marginTop: 16, textAlign: 'center', color: '#666' }}>
              Total: {disciplines.length} disciplines
            </div>
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col span={24}>
          <Card title="All Disciplines" extra={<BarChartOutlined />}>
            <Table
              columns={disciplineColumns}
              dataSource={disciplines}
              rowKey="discipline_code"
              pagination={{
                pageSize: 20,
                showSizeChanger: true,
                showQuickJumper: true,
                showTotal: (total, range) =>
                  `${range[0]}-${range[1]} of ${total} disciplines`,
              }}
              scroll={{ x: 400 }}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col span={24}>
          <Card title="Database Information">
            <div style={{ padding: '20px 0' }}>
              <p>
                <strong>Data Source:</strong> This database contains comprehensive athletics data 
                including competitions, athletes, events, and results from around the world.
              </p>
              <p>
                <strong>Coverage:</strong> The database spans multiple countries and includes 
                various athletics disciplines such as track and field events.
              </p>
              <p>
                <strong>Data Quality:</strong> Results include detailed performance metrics, 
                wind conditions (where applicable), and qualification status.
              </p>
              <p>
                <strong>Updates:</strong> Data is regularly synchronized and maintained to 
                ensure accuracy and completeness.
              </p>
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Stats;
