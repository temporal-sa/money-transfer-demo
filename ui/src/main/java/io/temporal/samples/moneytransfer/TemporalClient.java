package io.temporal.samples.moneytransfer;

import io.grpc.Metadata;
import io.grpc.stub.MetadataUtils;
import io.temporal.client.WorkflowClient;
import io.temporal.client.WorkflowClientOptions;
import io.temporal.client.schedules.ScheduleClient;
import io.temporal.client.schedules.ScheduleClientOptions;
import io.temporal.common.converter.CodecDataConverter;
import io.temporal.common.converter.DefaultDataConverter;
import io.temporal.samples.moneytransfer.dataconverter.CryptCodec;
import io.temporal.samples.moneytransfer.helper.ServerInfo;
import io.temporal.serviceclient.SimpleSslContextBuilder;
import io.temporal.serviceclient.WorkflowServiceStubs;
import io.temporal.serviceclient.WorkflowServiceStubsOptions;

import javax.net.ssl.SSLException;
import java.io.FileInputStream;
import java.io.FileNotFoundException;
import java.io.InputStream;
import java.util.Collections;

public class TemporalClient {

    public static WorkflowServiceStubsOptions.Builder getWorkflowServiceStubsOptionsBuilder() throws FileNotFoundException, SSLException {
        WorkflowServiceStubsOptions.Builder workflowServiceStubsOptionsBuilder =
                WorkflowServiceStubsOptions.newBuilder();

        if (!ServerInfo.getApiKey().equals("")) {
            workflowServiceStubsOptionsBuilder
                .addApiKey(() -> ServerInfo.getApiKey())
                .setEnableHttps(true);
        }
        else if (!ServerInfo.getCertPath().equals("") && !"".equals(ServerInfo.getKeyPath())) {
            InputStream clientCert = new FileInputStream(ServerInfo.getCertPath());
            InputStream clientKey = new FileInputStream(ServerInfo.getKeyPath());
            workflowServiceStubsOptionsBuilder.setSslContext(
                    SimpleSslContextBuilder.forPKCS8(clientCert, clientKey).build()
            );
        }
        else if (!ServerInfo.getAddress().equals("localhost:7233")){
            throw new RuntimeException("You must specify either an API KEY or mTLS certificates for a non local connection");
        }

        String targetEndpoint = ServerInfo.getAddress();
        workflowServiceStubsOptionsBuilder.setTarget(targetEndpoint);

        return workflowServiceStubsOptionsBuilder;
    }

    public static WorkflowServiceStubs getWorkflowServiceStubs() throws FileNotFoundException, SSLException {
        WorkflowServiceStubs service = null;

        if (!ServerInfo.getAddress().equals("localhost:7233")) {
            // if not local server, then use the workflowServiceStubsOptionsBuilder
            service = WorkflowServiceStubs.newServiceStubs(getWorkflowServiceStubsOptionsBuilder().build());
        } else {
            service = WorkflowServiceStubs.newLocalServiceStubs();
        }

        return service;
    }

    /*
        The Temporal client will insert headers required for API keys. If the service client is used, API key
        headers have to be manually added.
     */
    public static WorkflowServiceStubs getWorkflowServiceStubsWithHeaders() throws FileNotFoundException, SSLException {
        WorkflowServiceStubsOptions.Builder workflowServiceStubsOptionsBuilder = getWorkflowServiceStubsOptionsBuilder();

        if (!ServerInfo.getApiKey().isEmpty()) {
            Metadata.Key<String> namespace = Metadata.Key.of("temporal-namespace", Metadata.ASCII_STRING_MARSHALLER);

            Metadata metadata = new Metadata();
            metadata.put(namespace, ServerInfo.getNamespace());

            workflowServiceStubsOptionsBuilder
                    .setChannelInitializer(
                            (channel) -> {
                                channel.intercept(MetadataUtils.newAttachHeadersInterceptor(metadata));
                            });
        }

        WorkflowServiceStubs service = null;

        if (!ServerInfo.getAddress().equals("localhost:7233")) {
            // if not local server, then use the workflowServiceStubsOptionsBuilder
            service = WorkflowServiceStubs.newServiceStubs(workflowServiceStubsOptionsBuilder.build());
        } else {
            service = WorkflowServiceStubs.newLocalServiceStubs();
        }

        return service;
    }

    public static WorkflowClient get() throws FileNotFoundException, SSLException {
        WorkflowServiceStubs service = getWorkflowServiceStubs();
        WorkflowClientOptions.Builder builder = WorkflowClientOptions.newBuilder();

        // if environment variable ENCRYPT_PAYLOADS is set to true, then use CryptCodec
        if (System.getenv("ENCRYPT_PAYLOADS") != null && System.getenv("ENCRYPT_PAYLOADS").equals("true")) {
            builder.setDataConverter(
                    new CodecDataConverter(
                            DefaultDataConverter.newDefaultInstance(),
                            Collections.singletonList(new CryptCodec()),
                            true/* encode failure attributes */
                    )
            );
        }

        System.out.println("<<<<SERVER INFO>>>>:\n " + ServerInfo.getServerInfo());
        WorkflowClientOptions clientOptions = builder.setNamespace(ServerInfo.getNamespace()).build();

        // client that can be used to start and signal workflows
        WorkflowClient client = WorkflowClient.newInstance(service, clientOptions);
        return client;
    }

    public static ScheduleClient getScheduleClient() throws FileNotFoundException, SSLException {
        ScheduleClientOptions.Builder builder = ScheduleClientOptions.newBuilder();

        // if environment variable ENCRYPT_PAYLOADS is set to true, then use CryptCodec
        if (System.getenv("ENCRYPT_PAYLOADS") != null && System.getenv("ENCRYPT_PAYLOADS").equals("true")) {
            builder.setDataConverter(
                    new CodecDataConverter(
                            DefaultDataConverter.newDefaultInstance(),
                            Collections.singletonList(new CryptCodec()),
                            true/* encode failure attributes */
                    )
            );
        }

        System.out.println("<<<<SERVER INFO>>>>:\n " + ServerInfo.getServerInfo());
        ScheduleClientOptions clientOptions = builder.setNamespace(ServerInfo.getNamespace()).build();

        return ScheduleClient.newInstance(getWorkflowServiceStubsWithHeaders(), clientOptions);
    }
}
