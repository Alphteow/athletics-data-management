import React, { useState, useEffect } from 'react';
import { 
  Table, 
  Input, 
  Button, 
  Space, 
  Card, 
  Typography, 
  Tag, 
  message,
  Spin,
  Modal,
  Descriptions
} from 'antd';
import { SearchOutlined, EyeOutlined, CalendarOutlined, EnvironmentOutlined } from '@ant-design/icons';
import axios from 'axios';

const { Title } = Typography;
const { Search } = Input;

interface Competition {
  id: number;
  name: string;
  venue: string;
  area: string;
  country_name: string;
  ranking_category_name: string;
  start_date: string;
  end_date: string;
  season: number;
  has_results: boolean;
  disciplines: string[];
}

const Competitions: React.FC = () => {
  const [competitions, setCompetitions] = useState<Competition[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 10,
    total: 0,
  });
  const [selectedCompetition, setSelectedCompetition] = useState<Competition | null>(null);
  const [modalVisible, setModalVisible] = useState(false);

  useEffect(() => {
    fetchCompetitions();
  }, [pagination.current, pagination.pageSize, searchText]);

  const fetchCompetitions = async () => {
    setLoading(true);
    try {
      const response = await axios.get('http://localhost:5000/api/competitions', {
        params: {
          page: pagination.current,
          per_page: pagination.pageSize,
          search: searchText || undefined,
        },
      });

      setCompetitions(response.data.competitions);
      setPagination(prev => ({
        ...prev,
        total: response.data.total,
      }));
    } catch (error) {
      message.error('Failed to fetch competitions');
      console.error('Error fetching competitions:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleTableChange = (newPagination: any) => {
    setPagination(prev => ({
      ...prev,
      current: newPagination.current,
      pageSize: newPagination.pageSize,
    }));
  };

  const handleSearch = (value: string) => {
    setSearchText(value);
    setPagination(prev => ({ ...prev, current: 1 }));
  };

  const showCompetitionDetails = (competition: Competition) => {
    setSelectedCompetition(competition);
    setModalVisible(true);
  };

  const columns = [
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
      ellipsis: true,
      render: (text: string) => <strong>{text}</strong>,
    },
    {
      title: 'Venue',
      dataIndex: 'venue',
      key: 'venue',
      ellipsis: true,
      render: (text: string) => (
        <Space>
          <EnvironmentOutlined />
          {text}
        </Space>
      ),
    },
    {
      title: 'Country',
      dataIndex: 'country_name',
      key: 'country_name',
      render: (text: string) => <Tag color="blue">{text}</Tag>,
    },
    {
      title: 'Date',
      key: 'date',
      render: (record: Competition) => (
        <Space direction="vertical" size="small">
          <div>
            <CalendarOutlined /> {new Date(record.start_date).toLocaleDateString()}
          </div>
          {record.end_date !== record.start_date && (
            <div style={{ fontSize: '12px', color: '#666' }}>
              to {new Date(record.end_date).toLocaleDateString()}
            </div>
          )}
        </Space>
      ),
    },
    {
      title: 'Season',
      dataIndex: 'season',
      key: 'season',
      width: 80,
    },
    {
      title: 'Category',
      dataIndex: 'ranking_category_name',
      key: 'ranking_category_name',
      render: (text: string) => <Tag color="green">{text}</Tag>,
    },
    {
      title: 'Has Results',
      dataIndex: 'has_results',
      key: 'has_results',
      width: 100,
      render: (hasResults: boolean) => (
        <Tag color={hasResults ? 'success' : 'default'}>
          {hasResults ? 'Yes' : 'No'}
        </Tag>
      ),
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 100,
      render: (record: Competition) => (
        <Button
          type="link"
          icon={<EyeOutlined />}
          onClick={() => showCompetitionDetails(record)}
        >
          View
        </Button>
      ),
    },
  ];

  return (
    <div>
      <Title level={2}>Competitions</Title>
      
      <Card style={{ marginBottom: 16 }}>
        <Space direction="vertical" style={{ width: '100%' }}>
          <Search
            placeholder="Search competitions by name, venue, or country..."
            allowClear
            enterButton={<SearchOutlined />}
            size="large"
            onSearch={handleSearch}
            style={{ maxWidth: 400 }}
          />
        </Space>
      </Card>

      <Card>
        <Table
          columns={columns}
          dataSource={competitions}
          rowKey="id"
          loading={loading}
          pagination={{
            ...pagination,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) =>
              `${range[0]}-${range[1]} of ${total} competitions`,
          }}
          onChange={handleTableChange}
          scroll={{ x: 800 }}
        />
      </Card>

      <Modal
        title="Competition Details"
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={null}
        width={600}
      >
        {selectedCompetition && (
          <Descriptions bordered column={1}>
            <Descriptions.Item label="Name" span={2}>
              {selectedCompetition.name}
            </Descriptions.Item>
            <Descriptions.Item label="Venue">
              {selectedCompetition.venue}
            </Descriptions.Item>
            <Descriptions.Item label="Area">
              {selectedCompetition.area}
            </Descriptions.Item>
            <Descriptions.Item label="Country">
              <Tag color="blue">{selectedCompetition.country_name}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="Category">
              <Tag color="green">{selectedCompetition.ranking_category_name}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="Start Date">
              {new Date(selectedCompetition.start_date).toLocaleDateString()}
            </Descriptions.Item>
            <Descriptions.Item label="End Date">
              {new Date(selectedCompetition.end_date).toLocaleDateString()}
            </Descriptions.Item>
            <Descriptions.Item label="Season">
              {selectedCompetition.season}
            </Descriptions.Item>
            <Descriptions.Item label="Has Results">
              <Tag color={selectedCompetition.has_results ? 'success' : 'default'}>
                {selectedCompetition.has_results ? 'Yes' : 'No'}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="Disciplines">
              {selectedCompetition.disciplines?.map((discipline, index) => (
                <Tag key={index} color="purple">{discipline}</Tag>
              ))}
            </Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
    </div>
  );
};

export default Competitions;
